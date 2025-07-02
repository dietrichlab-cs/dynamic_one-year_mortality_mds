## Webapp

This branch contains the web application for the project. It is built using FastAPI as a backend with a vite/react frontend.

### Public deployment

This web application is deployed on a public server and can be accessed at the following URL:
[https://dietrichlab.de/PythonApps/dynamic_mds_paper/](https://dietrichlab.de/PythonApps/dynamic_mds_paper/)

### Local Deployment

#### vite app

To run the vite app locally, you need to have Node.js installed. After that, you can run the following commands inside the `dynamic_mds_paper` directory:

```bash
npm install
npm run dev
```

#### FastAPI app

Execute the following command to run the FastAPI app inside the `dynamic_mds_paper` directory:

```bash
pip install -r requirements.txt
export ENV=dev
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
