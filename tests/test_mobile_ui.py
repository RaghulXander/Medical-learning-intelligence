import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.routes.mobile_ui import _visible, read_default_home
from backend.core.authorization import Permission, has_permission
from backend.mobile_ui.schemas import MobileScreenDocument
from database.models import Base, User, UserRole


class MobileUiSchemaTests(unittest.TestCase):
    def test_bundled_home_document_is_valid(self):
        document = read_default_home()
        self.assertEqual(document.screenKey, "home")
        self.assertGreater(len(document.widgets), 0)

    def test_duplicate_widget_ids_are_rejected(self):
        document = read_default_home().model_dump(mode="json")
        document["widgets"].append(dict(document["widgets"][0]))
        with self.assertRaises(ValidationError):
            MobileScreenDocument.model_validate(document)

    def test_mobile_layout_permissions_are_admin_only(self):
        self.assertTrue(has_permission(UserRole.ADMIN, Permission.MOBILE_UI_PUBLISH))
        self.assertTrue(has_permission(UserRole.SUPER_ADMIN, Permission.MOBILE_UI_EDIT))
        self.assertFalse(has_permission(UserRole.REVIEWER, Permission.MOBILE_UI_PUBLISH))
        self.assertFalse(has_permission(UserRole.USER, Permission.MOBILE_UI_READ))

    def test_subscription_visibility_is_applied_server_side(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        try:
            free = User(email="free@example.com", name="Free", role=UserRole.USER, is_subscribed=False)
            subscribed = User(email="sub@example.com", name="Sub", role=UserRole.USER, is_subscribed=True)
            db.add_all([free, subscribed])
            db.commit()
            document = read_default_home()
            free_types = {item["type"] for item in _visible(document, free, "ANDROID")["widgets"]}
            subscribed_types = {item["type"] for item in _visible(document, subscribed, "ANDROID")["widgets"]}
            self.assertNotIn("continue_learning", free_types)
            self.assertIn("continue_learning", subscribed_types)
        finally:
            db.close()
            Base.metadata.drop_all(engine)


if __name__ == "__main__":
    unittest.main()
