import xml.etree.ElementTree as ET
import json

# --- XML Namespace Configuration ---
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
OMGDC_NS = "http://www.omg.org/spec/DD/20100524/DC"
OMGDI_NS = "http://www.omg.org/spec/DD/20100524/DI"

ET.register_namespace('', BPMN_NS)
ET.register_namespace('camunda', CAMUNDA_NS)
ET.register_namespace('bpmndi', BPMNDI_NS)
ET.register_namespace('omgdc', OMGDC_NS)
ET.register_namespace('omgdi', OMGDI_NS)

# --- Main Workflow Class ---
class Workflow:
    def __init__(self, id="Definitions_1", target_namespace="http://bpmn.io/schema/bpmn"):
        self.root = ET.Element(f"{{{BPMN_NS}}}definitions", id=id, targetNamespace=target_namespace)
        self.process = None

    def add_process(self, process):
        self.process = process
        self.root.append(process.element)

    def to_xml(self, filename):
        if self.process:
            self._generate_diagram()
        tree = ET.ElementTree(self.root)
        self._indent(self.root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def _generate_diagram(self):
        diagram = ET.SubElement(self.root, f"{{{BPMNDI_NS}}}BPMNDiagram", id="BPMNDiagram_1")
        plane = ET.SubElement(diagram, f"{{{BPMNDI_NS}}}BPMNPlane", id="BPMNPlane_1", bpmnElement=self.process.id)

        # Generate shapes
        for elem_id, info in self.process.positions.items():
            shape = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", id=f"{elem_id}_di", bpmnElement=elem_id)
            bounds = ET.SubElement(shape, f"{{{OMGDC_NS}}}Bounds", **info['coords'])

        # Generate edges
        for flow in self.process.element.findall(f'{{{BPMN_NS}}}sequenceFlow'):
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            source_info = self.process.positions.get(source_ref)
            target_info = self.process.positions.get(target_ref)

            if source_info and target_info:
                edge = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNEdge", id=f"{flow_id}_di", bpmnElement=flow_id)
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=str(int(source_info['coords']['x']) + int(source_info['coords']['width']))), y=str(int(source_info['coords']['y']) + int(source_info['coords']['height']) // 2))
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=target_info['coords']['x'], y=str(int(target_info['coords']['y']) + int(target_info['coords']['height']) // 2))

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

# --- Process and Element Classes ---
class Process:
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        self.id = id
        self.element = ET.Element(
            f"{{{BPMN_NS}}}process",
            id=id,
            isExecutable=str(is_executable).lower(),
            **{{f"{{{CAMUNDA_NS}}}historyTimeToLive": history_ttl}
        )
        self.elements = {}
        self.positions = {}
        self._x_pos = 150
        self._y_pos = 100

    def _add_element(self, element, elem_id, width, height):
        self.elements[elem_id] = element
        self.positions[elem_id] = {
            'coords': {'x': str(self._x_pos), 'y': str(self._y_pos), 'width': str(width), 'height': str(height)}
        }
        self._x_pos += width + 100

    def add_sequence_flow(self, id, source_ref, target_ref):
        return ET.SubElement(self.element, f"{{{BPMN_NS}}}sequenceFlow", id=id, sourceRef=source_ref, targetRef=target_ref)

class StartEvent:
    def __init__(self, process, id="StartEvent_1"):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}startEvent", id=id)
        process._add_element(self.element, id, 36, 36)

class EndEvent:
    def __init__(self, process, id="EndEvent_1"):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}endEvent", id=id)
        process._add_element(self.element, id, 36, 36)

class HumanTask:
    def __init__(self, process, id, name, meta=None, extension_meta=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}userTask", id=id, name=name, **(meta if meta else {{}}))
        if extension_meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for k, v in extension_meta.items():
                ET.SubElement(ext, f"{{{CAMUNDA_NS}}}meta", key=str(k)).text = str(v)
        process._add_element(self.element, id, 100, 80)

class ConnectorServiceTask:
    def __init__(self, process, id, name, url, method="GET", payload=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=id, name=name)
        ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
        connector = ET.SubElement(ext, f"{{{CAMUNDA_NS}}}connector")
        ET.SubElement(connector, f"{{{CAMUNDA_NS}}}connectorId").text = "http-connector"
        io = ET.SubElement(connector, f"{{{CAMUNDA_NS}}}inputOutput")
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="url").text = url
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="method").text = method
        if payload:
            ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="payload").text = json.dumps(payload)
        process._add_element(self.element, id, 100, 80)

class ScriptTask:
    def __init__(self, process, id, name, script_format, script):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}scriptTask", id=id, name=name, **{{f"{{{CAMUNDA_NS}}}scriptFormat": script_format}})
        ET.SubElement(self.element, f"{{{BPMN_NS}}}script").text = script
        process._add_element(self.element, id, 100, 80)

class ExclusiveGateway:
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name: attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", attrib=attribs)
        process._add_element(self.element, id, 50, 50)

class ParallelGateway:
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name: attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}parallelGateway", attrib=attribs)
        process._add_element(self.element, id, 50, 50)

# --- Example Usage (Now with consistent API and auto-diagramming) ---
if __name__ == "__main__":
    wf = Workflow()
    proc = Process()
    wf.add_process(proc)

    # Create elements by instantiating their classes
    StartEvent(proc, "StartEvent_1")
    HumanTask(proc, "Task_1", "Human Task", extension_meta={'x': 1, 'y': 2})
    ConnectorServiceTask(proc, "Task_2", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar2"})
    ConnectorServiceTask(proc, "Task_3", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar3"})
    ConnectorServiceTask(proc, "Task_4", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar4"})
    ScriptTask(proc, "Task_5", "Script Task", script_format="javascript", script="print('Script Task executed!')")
    ExclusiveGateway(proc, "Gateway_1", "Decision")
    ParallelGateway(proc, "Gateway_2", "Parallel Split")
    EndEvent(proc, "EndEvent_1")

    # Add sequence flows to connect the elements
    proc.add_sequence_flow("Flow_1", "StartEvent_1", "Task_1")
    proc.add_sequence_flow("Flow_2", "Task_1", "Task_2")
    proc.add_sequence_flow("Flow_3", "Task_2", "Task_3")
    proc.add_sequence_flow("Flow_4", "Task_3", "Task_4")
    proc.add_sequence_flow("Flow_5", "Task_4", "Task_5")
    proc.add_sequence_flow("Flow_6", "Task_5", "Gateway_1")
    proc.add_sequence_flow("Flow_7", "Gateway_1", "Gateway_2")
    proc.add_sequence_flow("Flow_8", "Gateway_2", "EndEvent_1")

    wf.to_xml("workflow_improved.bpmn")
    print("Generated improved workflow file: workflow_improved.bpmn")
