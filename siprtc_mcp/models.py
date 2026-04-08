from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CallRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    application_sid: str | None = Field(
        default=None,
        alias="ApplicationSid",
        description="Application SID to handle the call.",
    )
    from_number: str | None = Field(
        default=None,
        alias="From",
        description="Caller ID number with country code, e.g., 15677654321.",
        examples=["15677654321"],
    )
    to: str | None = Field(
        default=None,
        alias="To",
        description="Destination number or SIP endpoint (with country code for PSTN).",
        examples=["15677654321"],
    )
    url: str | None = Field(
        default=None,
        alias="Url",
        description="TinyML URL to execute when the call connects.",
        examples=["https://raw.githubusercontent.com/siprtc/public/master/answer.xml"],
    )
    method: Literal["GET", "POST"] | None = Field(
        default=None,
        alias="Method",
        description="HTTP verb for Url. Defaults to POST on the API side.",
    )
    status_callback: str | None = Field(
        default=None,
        alias="StatusCallback",
        description="Callback URL to receive call status events.",
    )
    status_callback_event: str | None = Field(
        default=None,
        alias="StatusCallbackEvent",
        description="Call progress events to report (initiated ringing answered completed).",
    )
    status_callback_method: Literal["GET", "POST"] | None = Field(
        default=None,
        alias="StatusCallbackMethod",
        description="HTTP verb for StatusCallback. Defaults to POST.",
    )
    record: str | None = Field(
        default=None,
        alias="Record",
        description="Whether to record the call (true/false).",
    )
    recording_status_callback: str | None = Field(
        default=None,
        alias="RecordingStatusCallback",
        description="Callback URL when recording becomes available.",
    )
    recording_status_callback_event: str | None = Field(
        default=None,
        alias="RecordingStatusCallbackEvent",
        description="Recording status events (in-progress completed absent).",
    )
    recording_status_callback_method: Literal["GET", "POST"] | None = Field(
        default=None,
        alias="RecordingStatusCallbackMethod",
        description="HTTP verb for RecordingStatusCallback. Defaults to POST.",
    )
    caller_name: str | None = Field(
        default=None,
        alias="CallerName",
        description="Caller name to use with the call.",
        examples=["Siprtc"],
    )
    play: str | None = Field(
        default=None,
        alias="Play",
        description="URL to an audio file to play after the call is answered.",
    )
    speak: str | None = Field(
        default=None,
        alias="Speak",
        description="Sentence to speak after the call is answered.",
    )
    send_digits: str | None = Field(
        default=None,
        alias="SendDigits",
        description="DTMF digits to send after connecting (e.g., ww1234#).",
    )
    timeout: str | None = Field(
        default=None,
        alias="Timeout",
        description="Ring timeout in seconds.",
    )
    tinyml: str | None = Field(
        default=None,
        alias="TinyML",
        description="Inline TinyML instructions to execute for the call.",
    )


class MessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    to: str = Field(
        alias="To",
        description="Destination phone number in E.164 format.",
    )
    body: str = Field(
        alias="Body",
        description="SMS message body.",
        max_length=1600,
    )
    from_number: str | None = Field(
        default=None,
        alias="From",
        description="Sender ID or Siprtc phone number in E.164 format.",
    )
    status_callback: str | None = Field(
        default=None,
        alias="StatusCallback",
        description="Callback URL for message status updates.",
    )
    status_callback_method: Literal["GET", "POST", "get", "post", "Get", "Post"] | None = Field(
        default=None,
        alias="StatusCallbackMethod",
        description="HTTP method for StatusCallback.",
    )
