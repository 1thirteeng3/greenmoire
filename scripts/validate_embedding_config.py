from core.config.embedding import load_embedding_config


def main() -> int:
    try:
        config = load_embedding_config()
    except ValueError as exc:
        print(f"[embedding-config] INVALID: {exc}")
        return 1

    print(
        "[embedding-config] OK: "
        f"provider={config.provider} model={config.model_name} dimension={config.dimension}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
