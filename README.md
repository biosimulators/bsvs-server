![Continuous Integration](https://github.com/biosimulations/biosim-server/actions/workflows/integrate.yml/badge.svg)
![Continuous Deployment](https://github.com/biosimulations/biosim-server/actions/workflows/deploy.yml/badge.svg)

# **`biosim-server`: Biosimulations Services**

This service utilizes separate containers for REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance.

_The REST API can be accessed via Swagger UI here:_ **[https://biosim.biosimulations.org/docs](https://biosim.biosimulations.org/docs)**

### **For Developers:**

`biosim-server` uses a microservices architecture which presents the following libraries:

- `api`: This library handles all requests including saving uploaded files, pending job creation, fetching results, and contains the user-facing endpoints.
- `common`: This library contains shared content.
- `workflows`: This library handles all job processing tasks for verification services such as job status adjustment, job retrieval, and comparison execution
- `worker`: This library performs all workflow tasks

**_Container management_** is handled by Kubernetes in Google Cloud. The full K8 config/spec can be found in the `kustomize` directory. **_Dependency management_** is handled by `poetry`.

#### Getting started:


### Notes:
- This application currently uses the Temporal durable execution technology to manage distributed and fault tolerant workflow tasks.

- If running temporal workflows in the pycharm debugger fails, please read https://youtrack.jetbrains.com/issue/PY-62467/TypeError-Task-object-is-not-callable-debugging-uvloop-with-asyncio-support-enabled
