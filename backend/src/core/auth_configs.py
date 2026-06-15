from dataclasses import dataclass


@dataclass(frozen=True)
class OtpFlowConfig:
    requires_existing_account: bool
    requires_unique_phone: bool


OTP_MAX_ATTEMPTS = 5
OTP_MAX_RESENDS = 2
OTP_COOLDOWN_MINUTES = 10

OTP_FLOW_CONFIGS: dict[str, OtpFlowConfig] = {
    "SIGNUP": OtpFlowConfig(
        requires_existing_account=False,
        requires_unique_phone=True,
    ),
    "LOGIN": OtpFlowConfig(
        requires_existing_account=True,
        requires_unique_phone=False,
    ),
}


def is_supported_otp_flow(flow: str) -> bool:
    return flow in OTP_FLOW_CONFIGS


def get_otp_flow_config(flow: str) -> OtpFlowConfig:
    try:
        return OTP_FLOW_CONFIGS[flow]
    except KeyError as exc:
        raise ValueError(f"Unsupported OTP flow: {flow}") from exc
