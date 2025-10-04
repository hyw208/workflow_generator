import xml.etree.ElementTree as ET

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"
ET.register_namespace('', BPMN_NS)
ET.register_namespace('camunda', CAMUNDA_NS)

class Workflow:
    def __init__(self, id="Definitions_1", target_namespace="http://bpmn.io/schema/bpmn"):
        self.root = ET.Element(
            f"{{{BPMN_NS}}}definitions",
            {
                "id": id,
                "targetNamespace": target_namespace,
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xmlns:bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
                "xmlns:omgdc": "http://www.omg.org/spec/DD/20100524/DC",
                "xmlns:omgdi": "http://www.omg.org/spec/DD/20100524/DI"
            }
        )
        self.processes = []

    def add_process(self, process):
        self.processes.append(process)
        self.root.append(process.element)

    def to_xml(self, filename):
        tree = ET.ElementTree(self.root)
        self._indent(self.root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def _indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            for child in elem:
                self._indent(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

class Process:
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        self.element = ET.Element(
            f"{{{BPMN_NS}}}process",
            id=id,
            isExecutable=str(is_executable).lower(),
            **{f"{{{CAMUNDA_NS}}}historyTimeToLive": history_ttl}
        )
        self.elements = {}

    def add_start_event(self, id="StartEvent_1"):
        start_event = ET.SubElement(self.element, f"{{{BPMN_NS}}}startEvent", id=id)
        self.elements[id] = start_event
        return start_event

    def add_user_task(self, id, name):
        user_task = ET.SubElement(self.element, f"{{{BPMN_NS}}}userTask", id=id, name=name)
        self.elements[id] = user_task
        return user_task

    def add_end_event(self, id="EndEvent_1"):
        end_event = ET.SubElement(self.element, f"{{{BPMN_NS}}}endEvent", id=id)
        self.elements[id] = end_event
        return end_event

    def add_sequence_flow(self, id, source_ref, target_ref):
        flow = ET.SubElement(
            self.element,
            f"{{{BPMN_NS}}}sequenceFlow",
            id=id,
            sourceRef=source_ref,
            targetRef=target_ref
        )
        return flow

class HumanTask:
    def __init__(self, process, id, name, meta=None, extension_meta=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}userTask", id=id, name=name, **(meta if meta else {}))
        if extension_meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for k, v in extension_meta.items():
                meta_elem = ET.SubElement(ext, f"{{{CAMUNDA_NS}}}meta", key=str(k))
                meta_elem.text = str(v)
        process.elements[id] = self.element

class DelegateServiceTask:
    def __init__(self, process, id, name, implementation):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=id, name=name)
        self.element.set(f"{{{CAMUNDA_NS}}}class", implementation)
        process.elements[id] = self.element

class ConnectorServiceTask:
    def __init__(self, process, id, name, url, method="GET", payload=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=id, name=name)
        # Remove camunda:type="connector" (invalid on serviceTask)
        # Add <extensionElements> and put <camunda:connector> inside
        extension_elements = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
        connector = ET.SubElement(extension_elements, f"{{{CAMUNDA_NS}}}connector")
        ET.SubElement(connector, f"{{{CAMUNDA_NS}}}connectorId").text = "http-connector"
        input_output = ET.SubElement(connector, f"{{{CAMUNDA_NS}}}inputOutput")
        input_param_url = ET.SubElement(input_output, f"{{{CAMUNDA_NS}}}inputParameter", name="url")
        input_param_url.text = url
        input_param_method = ET.SubElement(input_output, f"{{{CAMUNDA_NS}}}inputParameter", name="method")
        input_param_method.text = method
        if payload is not None:
            input_param_payload = ET.SubElement(input_output, f"{{{CAMUNDA_NS}}}inputParameter", name="payload")
            import json
            input_param_payload.text = json.dumps(payload)
        process.elements[id] = self.element

class ExternalServiceTask:
    def __init__(self, process, id, name, topic):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=id, name=name)
        self.element.set(f"{{{CAMUNDA_NS}}}type", "external")
        self.element.set(f"{{{CAMUNDA_NS}}}topic", topic)
        process.elements[id] = self.element

class ScriptTask:
    def __init__(self, process, id, name, script_format, script):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}scriptTask", id=id, name=name)
        self.element.set(f"{{{CAMUNDA_NS}}}scriptFormat", script_format)
        script_elem = ET.SubElement(self.element, f"{{{BPMN_NS}}}script")
        script_elem.text = script
        process.elements[id] = self.element

class ExclusiveGateway:
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name:
            attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", attrib=attribs)
        process.elements[id] = self.element

class ParallelGateway:
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name:
            attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}parallelGateway", attrib=attribs)
        process.elements[id] = self.element

# Example usage:
if __name__ == "__main__":
    wf = Workflow()
    proc = Process()
    wf.add_process(proc)

    proc.add_start_event("StartEvent_1")
    HumanTask(proc, "Task_1", "Human Task", extension_meta={'x':1, 'y': 2})
    # DelegateServiceTask(proc, "Task_2", "Service Task", implementation="my.ServiceClass")
    ConnectorServiceTask(proc, "Task_2", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar2"})
    ConnectorServiceTask(proc, "Task_3", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar3"})
    ConnectorServiceTask(proc, "Task_4", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar4"})
    # ExternalServiceTask(proc, "Task_4", "External Task", topic="myTopic")
    ScriptTask(proc, "Task_5", "Script Task", script_format="javascript", script="print('Script Task executed!')")
    ExclusiveGateway(proc, "Gateway_1", "Decision")
    ParallelGateway(proc, "Gateway_2", "Parallel Split")
    proc.add_end_event("EndEvent_1")
    proc.add_sequence_flow("Flow_1", "StartEvent_1", "Task_1")
    proc.add_sequence_flow("Flow_2", "Task_1", "Task_2")
    proc.add_sequence_flow("Flow_3", "Task_2", "Task_3")
    proc.add_sequence_flow("Flow_4", "Task_3", "Task_4")
    proc.add_sequence_flow("Flow_5", "Task_4", "Task_5")
    proc.add_sequence_flow("Flow_6", "Task_5", "Gateway_1")
    proc.add_sequence_flow("Flow_7", "Gateway_1", "Gateway_2")
    proc.add_sequence_flow("Flow_8", "Gateway_2", "EndEvent_1")

    wf.to_xml("workflow.bpmn")
