"""Strict native screen schema mirrored by the shared TypeScript package."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Audience = Literal["ALL", "AUTHENTICATED", "FREE", "SUBSCRIBED"]
Platform = Literal["ALL", "IOS", "ANDROID"]


class WidgetBase(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    enabled: bool
    order: int = Field(ge=0, le=10000)
    audience: Audience = "ALL"
    platforms: list[Platform] = Field(default_factory=lambda: ["ALL"], min_length=1, max_length=3)
    rolloutPercentage: int = Field(default=100, ge=0, le=100)


class GoalProgressProps(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    dailyGoal: int = Field(ge=1, le=500)
    actionLabel: str = Field(min_length=1, max_length=80)


class ContinueLearningProps(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    actionLabel: str = Field(min_length=1, max_length=80)


class FocusAreaProps(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    actionLabel: str = Field(min_length=1, max_length=80)


class CustomMockProps(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=300)


class QuickPresetsProps(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    viewAllLabel: str = Field(min_length=1, max_length=80)
    limit: int = Field(ge=1, le=10)


class GoalProgressWidget(WidgetBase):
    type: Literal["goal_progress"]
    props: GoalProgressProps


class ContinueLearningWidget(WidgetBase):
    type: Literal["continue_learning"]
    props: ContinueLearningProps


class FocusAreaWidget(WidgetBase):
    type: Literal["focus_area"]
    props: FocusAreaProps


class CustomMockWidget(WidgetBase):
    type: Literal["custom_mock"]
    props: CustomMockProps


class QuickPresetsWidget(WidgetBase):
    type: Literal["quick_presets"]
    props: QuickPresetsProps


MobileWidget = Annotated[
    Union[
        GoalProgressWidget,
        ContinueLearningWidget,
        FocusAreaWidget,
        CustomMockWidget,
        QuickPresetsWidget,
    ],
    Field(discriminator="type"),
]


class MobileScreenDocument(StrictModel):
    schemaVersion: Literal[1]
    screenKey: Literal["home"]
    minimumAppVersion: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    cacheTtlSeconds: int = Field(default=900, ge=60, le=86400)
    widgets: list[MobileWidget] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_widget_ids(self):
        ids = [widget.id for widget in self.widgets]
        if len(ids) != len(set(ids)):
            raise ValueError("Widget IDs must be unique")
        return self


class PublishMobileScreenRequest(StrictModel):
    document: MobileScreenDocument
    expectedVersion: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=500)
