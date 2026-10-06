import os
import sys
import importlib.util
import uvicorn

def main():
    root = os.getcwd()
    app_path = os.path.join(root, "app.py")
    if not os.path.exists(app_path):
        root = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(root, "app.py")
    sys.path.insert(0, root)
    spec = importlib.util.spec_from_file_location("adc_webapp", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run(module.app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")

if __name__ == "__main__":
    main()
