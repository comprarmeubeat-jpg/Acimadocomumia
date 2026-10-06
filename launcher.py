import os
import uvicorn

def main():
    port=int(os.getenv("PORT","10000"))
    uvicorn.run("app:app",host="0.0.0.0",port=port,proxy_headers=True,forwarded_allow_ips="*")

if __name__=="__main__":
    main()
