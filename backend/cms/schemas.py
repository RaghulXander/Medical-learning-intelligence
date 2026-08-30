"""Strict CMS document schemas mirrored by the web Zod contract."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Audience = Literal["ALL", "GUEST", "AUTHENTICATED"]


class CmsAction(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    action: Literal["START_DIAGNOSTIC", "OPEN_STUDENT_HUB", "OPEN_SIGNUP", "CONTACT"]


class HeroProps(StrictModel):
    eyebrow: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=160)
    highlight: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=600)
    primaryAction: CmsAction
    secondaryAction: CmsAction | None = None


class DiagnosticProps(StrictModel):
    badge: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    questionCount: int = Field(ge=1, le=20)
    durationMinutes: int = Field(ge=1, le=60)
    actionLabel: str = Field(min_length=1, max_length=80)


class StatItem(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=40)


class StatsProps(StrictModel):
    items: list[StatItem] = Field(min_length=1, max_length=8)


class FeatureItem(StrictModel):
    icon: Literal["microscope", "zap", "shield-check", "brain-circuit", "book-open"]
    title: str = Field(min_length=1, max_length=140)
    description: str = Field(min_length=1, max_length=500)
    tag: str = Field(min_length=1, max_length=80)


class FeatureProps(StrictModel):
    badge: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    items: list[FeatureItem] = Field(min_length=1, max_length=12)


class ContentProps(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)


class ContactProps(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)
    actionLabel: str = Field(min_length=1, max_length=80)


class SectionBase(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    enabled: bool
    order: int = Field(ge=0, le=10000)
    audience: Audience


class HeroSection(SectionBase):
    type: Literal["hero"]
    props: HeroProps


class DiagnosticSection(SectionBase):
    type: Literal["diagnostic_cta"]
    props: DiagnosticProps


class StatsSection(SectionBase):
    type: Literal["stats"]
    props: StatsProps


class FeatureSection(SectionBase):
    type: Literal["feature_grid"]
    props: FeatureProps


class ContentSection(SectionBase):
    type: Literal["content_block"]
    props: ContentProps


class ContactSection(SectionBase):
    type: Literal["contact_cta"]
    props: ContactProps


CmsSection = Annotated[
    Union[HeroSection, DiagnosticSection, StatsSection, FeatureSection, ContentSection, ContactSection],
    Field(discriminator="type"),
]


class SiteMetadata(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)


class LandingPageDocument(StrictModel):
    schemaVersion: Literal[1]
    documentVersion: datetime
    site: SiteMetadata
    sections: list[CmsSection] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def section_ids_are_unique(self):
        ids = [section.id for section in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("Section IDs must be unique")
        return self


class PublishLandingPageRequest(StrictModel):
    document: LandingPageDocument
    baseSha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    message: str | None = Field(default=None, max_length=160)


class RollbackLandingPageRequest(StrictModel):
    baseSha: str = Field(pattern=r"^[0-9a-f]{40}$")
