import base64
import json
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from backend.cms.github_publisher import (
    CmsGitHubSettings,
    CmsPublishConflict,
    GitHubContentPublisher,
    read_local_document,
)
from backend.cms.schemas import LandingPageDocument
from backend.core.authorization import Permission, has_permission
from database.models import UserRole


class TestCmsSchema(unittest.TestCase):
    def test_repository_document_is_valid(self):
        document = LandingPageDocument.model_validate(read_local_document())
        self.assertEqual(document.schemaVersion, 1)
        self.assertGreater(len(document.sections), 0)

    def test_duplicate_section_ids_are_rejected(self):
        document = read_local_document()
        document["sections"].append(dict(document["sections"][0]))
        with self.assertRaises(ValidationError):
            LandingPageDocument.model_validate(document)

    def test_cms_permissions_are_admin_only(self):
        self.assertTrue(has_permission(UserRole.SUPER_ADMIN, Permission.CONTENT_PUBLISH))
        self.assertTrue(has_permission(UserRole.ADMIN, Permission.CONTENT_PUBLISH))
        self.assertFalse(has_permission(UserRole.REVIEWER, Permission.CONTENT_PUBLISH))
        self.assertFalse(has_permission(UserRole.USER, Permission.CONTENT_READ))


class TestGitHubContentPublisher(unittest.TestCase):
    def setUp(self):
        self.settings = CmsGitHubSettings(
            owner="owner",
            repository="repo",
            branch="main",
            content_path="apps/web/content/landing-page.json",
            token="server-token",
        )
        self.publisher = GitHubContentPublisher(self.settings)
        self.document = read_local_document()

    @staticmethod
    def github_file_response(document, sha="a" * 40):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "sha": sha,
            "content": base64.b64encode(json.dumps(document).encode()).decode(),
        }
        return response

    @patch("backend.cms.github_publisher.requests.get")
    def test_reads_and_decodes_repository_content(self, get):
        get.return_value = self.github_file_response(self.document)
        document, sha = self.publisher.get_document()
        self.assertEqual(document["schemaVersion"], 1)
        self.assertEqual(sha, "a" * 40)
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer server-token")

    @patch("backend.cms.github_publisher.requests.get")
    def test_rejects_stale_base_sha_before_writing(self, get):
        get.return_value = self.github_file_response(self.document, sha="b" * 40)
        with self.assertRaises(CmsPublishConflict):
            self.publisher.publish(self.document, "a" * 40, "cms: update")

    @patch("backend.cms.github_publisher.requests.put")
    @patch("backend.cms.github_publisher.requests.get")
    def test_publishes_with_current_sha(self, get, put):
        get.return_value = self.github_file_response(self.document)
        put_response = Mock()
        put_response.ok = True
        put_response.status_code = 200
        put_response.json.return_value = {
            "commit": {"sha": "c" * 40, "html_url": "https://github.test/commit"},
            "content": {"sha": "d" * 40},
        }
        put.return_value = put_response
        result = self.publisher.publish(self.document, "a" * 40, "cms: update")
        self.assertEqual(result["commit_sha"], "c" * 40)
        self.assertEqual(put.call_args.kwargs["json"]["sha"], "a" * 40)


if __name__ == "__main__":
    unittest.main()
