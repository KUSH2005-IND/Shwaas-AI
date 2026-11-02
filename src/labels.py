"""Versioned Coswara proxy mapping. No jobs execute on import."""
NORMAL = {"healthy", "no_resp_illness_exposed"}
ABNORMAL = {"resp_illness_not_identified", "positive_mild", "positive_moderate"}
LABEL_VERSION = "coswara-status-proxy-v1"

def map_label(status):
    if not isinstance(status, str):
        return -1
    if status in NORMAL:
        return 0
    if status in ABNORMAL:
        return 1
    return -1

if __name__ == "__main__":
    from src.common import run_cli
    from src.prepare import main
    run_cli(main)
