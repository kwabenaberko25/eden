import os
import pytest
from eden.app import Eden
from eden.config import Environment, Config

def test_session_https_only_behavior():
    # 1. Debug mode = True -> https_only should be False
    app_debug = Eden(debug=True, secret_key="test")
    app_debug.setup_defaults()
    
    session_mw = next(m for m in app_debug._middleware_stack if m[0].__name__ == "SessionMiddleware")
    assert session_mw[1]["https_only"] is False, "https_only should be False when debug=True"

    # 2. Debug mode = False, Env = dev -> https_only should be False
    config_dev = Config(env="dev", secret_key="test", debug=False)
    app_dev = Eden(config=config_dev)
    app_dev.setup_defaults()
    
    session_mw = next(m for m in app_dev._middleware_stack if m[0].__name__ == "SessionMiddleware")
    assert session_mw[1]["https_only"] is False, "https_only should be False when in 'dev' environment"

    # 3. Debug mode = False, Env = prod -> https_only should be True
    config_prod = Config(env="prod", secret_key="test", debug=False)
    app_prod = Eden(config=config_prod)
    app_prod.setup_defaults()
    
    session_mw = next(m for m in app_prod._middleware_stack if m[0].__name__ == "SessionMiddleware")
    assert session_mw[1]["https_only"] is True, "https_only MUST be True in 'prod' environment with debug=False"

if __name__ == "__main__":
    # Manual run support
    try:
        test_session_https_only_behavior()
        print("[OK] CSRF/Session Security logic verified!")
    except Exception as e:
        print(f"[FAILED] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
