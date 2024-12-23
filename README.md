![Continuous Integration](https://github.com/biosimulators/bsvs-server/actions/workflows/integrate.yml/badge.svg)
![Continuous Deployment](https://github.com/biosimulators/bsvs-server/actions/workflows/deploy.yml/badge.svg)

# **`bsvs-server`: Backend for Biological Simulation Verification Service _(B.S.V.S.)_**

This service utilizes separate containers for REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance.

_The REST API can be accessed via Swagger UI here:_ **[https://biochecknet.biosimulations.org/docs](https://biochecknet.biosimulations.org/docs)**

### **For Developers:**

`bsvs-server` uses a microservices architecture which presents the following libraries:

- `gateway`: This library handles all requests including saving uploaded files, pending job creation, fetching results, and contains the user-facing endpoints.
- `shared`: This library contains shared content.
- `worker`: This library handles all job processing tasks for verification services such as job status adjustment, job retrieval, and comparison execution.

**_Container management_** is handled by Kubernetes in Google Cloud. The full K8 config/spec can be found in the `kustomize` directory. **_Dependency management_** is handled by `poetry`.

#### Getting started:


### Notes:
- This application currently uses MongoDB as the database store in which jobs are read/written. Database access is given to both the `api` and `worker` libraries. Such database access is 
executed/implemented with the use of a `Supervisor` singleton.

