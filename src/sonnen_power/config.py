from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")

    # sonnenBatterie HTTP API — reachable from the collector pod.
    sonnen_base_url: str = Field(alias="SONNEN_BASE_URL")
    sonnen_auth_token: str | None = Field(None, alias="SONNEN_AUTH_TOKEN")
    poll_interval_seconds: int = Field(15, alias="POLL_INTERVAL_SECONDS")

    decision_interval_seconds: int = Field(60, alias="DECISION_INTERVAL_SECONDS")
    execute_actions: bool = Field(False, alias="EXECUTE_ACTIONS")

    # Wake-on-LAN target (control plane) — passercluster uses tailscale
    # today; keep this optional for the eventual bare-metal case.
    control_plane_mac_address: str | None = Field(None, alias="CONTROL_PLANE_MAC_ADDRESS")
    wol_broadcast_address: str = Field("192.168.179.255", alias="WOL_BROADCAST_ADDRESS")
    wol_port: int = Field(9, alias="WOL_PORT")

    cluster_api_host: str | None = Field(None, alias="CLUSTER_API_HOST")
    cluster_api_port: int = Field(6443, alias="CLUSTER_API_PORT")

    # Folding@Home workload scaling targets.
    folding_namespace: str = Field("folding", alias="FOLDING_NAMESPACE")
    folding_deployment: str = Field("folding", alias="FOLDING_DEPLOYMENT")
    folding_burn_replicas: int = Field(1, alias="FOLDING_BURN_REPLICAS")

    # Policy thresholds.
    soc_scale_down_threshold: int = Field(35, alias="SOC_SCALE_DOWN_THRESHOLD")
    soc_low_recovery: int = Field(40, alias="SOC_LOW_RECOVERY")
    soc_burn_threshold: int = Field(70, alias="SOC_BURN_THRESHOLD")
    soc_scale_up_threshold: int = Field(65, alias="SOC_SCALE_UP_THRESHOLD")
    min_surplus_w_for_burn: int = Field(500, alias="MIN_SURPLUS_W_FOR_BURN")
    surplus_drop_w: int = Field(200, alias="SURPLUS_DROP_W")
    action_cooldown_minutes: int = Field(30, alias="ACTION_COOLDOWN_MINUTES")
    log_level: str = Field("INFO", alias="LOG_LEVEL")


def load_settings() -> Settings:
    return Settings()
