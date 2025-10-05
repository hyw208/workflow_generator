# Camunda Workflow Generator from Excel

This project provides a way to generate Camunda BPMN 2.0 workflows from a simple Excel spreadsheet. This allows non-developers to define and modify workflows easily.

## Features

*   **Excel-based Workflow Definition**: Define your workflow steps in a simple Excel spreadsheet.
*   **BPMN 2.0 Generation**: Automatically generate a valid BPMN 2.0 XML file from the Excel file.
*   **Supports Common BPMN Elements**: Supports Start Events, End Events, User Tasks, Service Tasks (with connector), and Exclusive Gateways.
*   **Configurable Task Metadata**: Add custom metadata to user tasks to drive UI components or other logic.
*   **Helper Scripts**: Includes scripts to interact with the Camunda REST API, such as fetching user task metadata.

## Prerequisites

*   [Python 3](https://www.python.org/downloads/)
*   [Docker](https://www.docker.com/products/docker-desktop)

## Installation

1.  Clone this repository.
2.  Install the Python dependencies:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

## How it Works

The core of this project is the `workflow_gen.py` script, which reads an Excel file (`workflows.xlsx`) and generates a BPMN 2.0 XML file.

### Excel File Structure

The `workflows.xlsx` file can contain multiple sheets, with each sheet representing a separate workflow. The following columns are used to define the workflow:

| Column      | Description                                                                                                                            | Example                                                              |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------- |
| `TopElm`    | The top-level element in the BPMN file. Use `PROCESS` for workflow steps.                                                              | `PROCESS`                                                            |
| `Seq`       | A unique sequence number for each step in the workflow. This is used to link the steps together.                                       | `1`                                                                  |
| `BPMNElm`   | The type of BPMN element for this step.                                                                                                | `StartEvent`, `UserTask`, `ServiceTask`, `ExclusiveGateway`, `EndEvent` |
| `Id`        | A unique ID for the BPMN element.                                                                                                      | `StartEvent_1`, `Task_ApproveRequest`                                |
| `Name`      | A user-friendly name for the BPMN element.                                                                                             | `Request Approval`                                                   |
| `Next`      | The `Seq` number of the next step in the workflow. For gateways, you can define conditional flows.                                     | `2` or `${approved == true}: 3, ${approved == false}: 4`             |
| `Config`    | Configuration for the BPMN element, such as the URL and method for a service task.                                                     | `url=http://localhost:8081, method=POST`                             |
| `Meta`      | Custom metadata to be added to the BPMN element. This is useful for storing extra information, like UI hints.                          | `button1=Approve, button2=Reject`                                    |
| `ErrorRef`  | For End Events, you can specify an error to throw.                                                                                     | `Error_1`                                                            |

### Generating the BPMN File

To generate the BPMN file, run the `workflow_gen.py` script:

```bash
python workflow_gen.py
```

This will read the `workflows.xlsx` file and generate a new BPMN file for each sheet (e.g., `approval_generated.bpmn`).

## Running the Workflow

### 1. Run Camunda with Docker

A `Dockerfile` is provided to build a custom image.

First, build the custom Camunda image:

```bash
docker build -t camunda-custom:7.20.0 .
```

Then, run the container. If you have a previous container named `camunda-custom`, you can remove it first.

```bash
docker rm -f camunda-custom
docker run -d -p 8080:8080 --name camunda-custom camunda-custom:7.20.0
```

### 2. Deploy the Workflows

Deploy the generated BPMN files to your Camunda instance using the Camunda REST API. Here are examples for the `approval`, `rsa`, and `main` workflows:

```bash
# Deploy approval workflow
curl -u demo:demo -F "deployment-name=approval-deployment" -F "deploy-changed-only=true" -F "approval.bpmn=@approval_generated.bpmn" http://localhost:8080/engine-rest/deployment/create

# Deploy rsa workflow
curl -u demo:demo -F "deployment-name=rsa-deployment" -F "deploy-changed-only=true" -F "rsa.bpmn=@rsa_generated.bpmn" http://localhost:8080/engine-rest/deployment/create

# Deploy main workflow
curl -u demo:demo -F "deployment-name=main-deployment" -F "deploy-changed-only=true" -F "main.bpmn=@main_generated.bpmn" http://localhost:8080/engine-rest/deployment/create
```

### 3. Start the Flask API for Service Tasks

The `echo_flask_api.py` script is a simple Flask application that can be used as a target for a service task. Run it in a separate terminal:

```bash
python echo_flask_api.py
```
You will see logging statements in the console when a service task calls the API.

## Interacting with the Workflow: A Step-by-Step Example

This example demonstrates a scenario where the `main_process` calls the `rsa_process`, which in turn calls the `approval_process`.

1.  **Start the `main_process`**
    Access the Camunda UI at `http://localhost:8080` (credentials: `demo`/`demo`) and start the `main_process`.

2.  **Complete the First User Task (main process)**
    The main process will wait for a user task to be completed. Find the task ID in the Camunda UI and use the following `curl` command to complete it (replace the task ID with your actual task ID):

    ```bash
    curl -X POST \
        -u demo:demo \
        http://localhost:8080/engine-rest/task/{your_task_id}/complete \
        -H 'Content-Type: application/json' \
        -d '{"variables": {"x": {"value": true, "type": "Boolean"},"y": {"value": "Task completed via API", "type": "String"}}}'
    ```

3.  **Complete the Second User Task (rsa process)**
    After the previous task is completed, a new user task will be created in the `rsa_process`. Complete it using its task ID:

    ```bash
    curl -X POST \
        -u demo:demo \
        http://localhost:8080/engine-rest/task/{your_task_id}/complete \
        -H 'Content-Type: application/json' \
        -d '{"variables": {"x": {"value": true, "type": "Boolean"},"y": {"value": "Task completed via API", "type": "String"}}}'
    ```

4.  **Complete the Third User Task (approval process)**
    Finally, a user task in the `approval_process` is created. You can either approve or reject it.

    *   **To approve:**
        ```bash
        curl -X POST \
            -u demo:demo \
            http://localhost:8080/engine-rest/task/{your_task_id}/complete \
            -H 'Content-Type: application/json' \
            -d '{"variables": {"approved": {"value": true, "type": "Boolean"},"rejection_reason": {"value": "approved by user", "type": "String"}}}'
        ```
    *   **To reject:**
        ```bash
        curl -X POST \
            -u demo:demo \
            http://localhost:8080/engine-rest/task/{your_task_id}/complete \
            -H 'Content-Type: application/json' \
            -d '{"variables": {"approved": {"value": false, "type": "Boolean"},"rejection_reason": {"value": "Test rejection", "type": "String"}}}'
        ```
    If you approve, the main workflow will complete. If you reject, the user task in the `rsa_process` will be re-created.

## Advanced Topics

### Use user task metadata to drive workflow next step

To retrieves custom static metadata for a user task, which is useful for dynamically generating UI elements.

1.  Get the `process_definition_id` from a running `process_instance_id`:
    ```bash
    curl http://localhost:8080/engine-rest/process-instance/{process_instance_id}
    ```
2.  Get the BPMN XML for the process definition:
    ```bash
    curl http://localhost:8080/engine-rest/process-definition/{definitionId}/xml
    ```
3.  Find the user task and parse the custom metadata
    ```xml
    <userTask id="Task3" name="Human Task - ABC" camunda:formKey="x/y/z/abc.html">
      <extensionElements>
        <camunda:meta key="RSA">1</camunda:meta>
        <camunda:meta key="ACK">2</camunda:meta>
      </extensionElements>
    </userTask>
    ```
4.  Use custom metadata to render user task UI, e.g 2 buttons on UI. Imagine there is exclusive gateway and clicking on button 'RSA' takes user to next step by completing current task

    ```json
    POST /engine-rest/task/{id}/complete
    {
      "variables": {
        "user_decision": {"value": "RSA", "type": "String"}
      }
    }
    ```
5.  This advances the workflow to the next step.

### Task Listener Events

You can use Task Listeners to execute custom logic at different points in the task lifecycle (`create`, `assignment`, `complete`, `delete`, `update`).

**Example:**
```xml
<userTask id="managerApproval" name="Manager Approval">
  <extensionElements>
    <camunda:taskListener event="create" class="com.example.ManagerAssignmentListener" />
  </extensionElements>
</userTask>
```
```java
@Component
public class ManagerAssignmentListener implements TaskListener {
    @Override
    public void notify(DelegateTask delegateTask) {
        // Logic to assign the task, set priority, due date, etc.
        String assignee = determineAssignee(...);
        delegateTask.setAssignee(assignee);
    }
}
```

### Execution Listener Events for Sub-processes

You can use Execution Listeners on `callActivity` elements to execute logic when a sub-process starts or ends. This is very useful to build the parent-child workflow relationship.

**Example:**
```xml
<callActivity id="callSubProcess" name="Call Sub-Process" calledElement="approvalSubProcess">
    <extensionElements>
        <camunda:executionListener event="start" class="com.example.SubProcessStartListener" />
        <camunda:executionListener event="end" class="com.example.SubProcessEndListener" />
    </extensionElements>
</callActivity>
```
```java
@Component
public class SubProcessStartListener implements ExecutionListener {
    @Override
    public void notify(DelegateExecution execution) throws Exception {
        // Logic to execute before the sub-process starts
        execution.setVariable("parentProcessId", execution.getProcessInstanceId());
    }
}
```
