![Continuous Integration](https://github.com/biosimulators/bsvs-server/actions/workflows/integrate.yml/badge.svg)
![Continuous Deployment](https://github.com/biosimulators/bsvs-server/actions/workflows/deploy.yml/badge.svg)

# **`bsvs-server`: Backend for Biological Simulation Verification Service _(B.S.V.S.)_**

_This service utilizes separate containers for REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance._

**The REST API can be accessed via Swagger UI here: [https://biochecknet.biosimulations.org/docs](https://biochecknet.biosimulations.org/docs)**

### **For Developers:**

### This application ("verification-server") uses a microservices architecture which presents the following libraries:

- `api`: This library handles all requests including saving uploaded files, pending job creation, fetching results, and contains the user-facing endpoints.
- `shared`: This library contains shared content.
- `worker`: This library handles all job processing tasks for verification services such as job status adjustment, job retrieval, and comparison execution.

#### Getting started:

### Dependency management scopes are handled as follows:

### Notes:
- This application currently uses MongoDB as the database store in which jobs are read/written. Database access is given to both the `api` and `worker` libraries. Such database access is 
executed/implemented with the use of a `Supervisor` singleton.

