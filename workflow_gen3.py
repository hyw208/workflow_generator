"""
This script provides a Python-based API for programmatically generating
BPMN 2.0 workflow XML files, including diagram information, which can be
used in engines like Camunda.
"""

import xml.etree.ElementTree as ET
import json
import logging

# --- Constants ---
# XML Namespaces
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
OMGDC_NS = "http://www.omg.org/spec/DD/20100524/DC"
OMGDI_NS = "http://www.omg.org/spec/DD/20100524/DI"

# Diagram Element Dimensions
START_EVENT_WIDTH = 36
START_EVENT_HEIGHT = 36
END_EVENT_WIDTH = 36
END_EVENT_HEIGHT = 36
TASK_WIDTH = 100
TASK_HEIGHT = 80
GATEWAY_WIDTH = 50
GATEWAY_HEIGHT = 50
HORIZONTAL_SPACING = 100

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def register_namespaces():
    """Registers the necessary BPMN and Camunda XML namespaces."""
    ET.register_namespace('', BPMN_NS)
    ET.register_namespace('camunda', CAMUNDA_NS)
    ET.register_namespace('bpmndi', BPMNDI_NS)
    ET.register_namespace('omgdc', OMGDC_NS)
    ET.register_namespace('omgdi', OMGDI_NS)

register_namespaces()

# --- Main Workflow Class ---
class Workflow:
    """Represents the entire BPMN workflow, including the diagram."""
    def __init__(self, id="Definitions_1", target_namespace="http://bpmn.io/schema/bpmn"):
        """
        Initializes the Workflow.
        Args:
            id (str): The ID of the definitions element.
            target_namespace (str): The target namespace for the BPMN file.
        """
        self.root = ET.Element(f"{{{BPMN_NS}}}definitions", id=id, targetNamespace=target_namespace)
        self.process = None

    def add_process(self, process):
        """
        Adds a Process to the workflow.
        Args:
            process (Process): The Process object to add.
        """
        self.process = process
        self.root.append(process.element)

    def to_xml(self, filename):
        """
        Generates the BPMN XML file, including the diagram.
        Args:
            filename (str): The name of the output XML file.
        """
        if self.process:
            self._generate_diagram()
        tree = ET.ElementTree(self.root)
        self._indent(self.root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        logging.info(f"Successfully generated workflow file: {filename}")

    def _generate_diagram(self):
        """Generates the BPMNDI diagram part of the XML."""
        diagram = ET.SubElement(self.root, f"{{{BPMNDI_NS}}}BPMNDiagram", id="BPMNDiagram_1")
        plane = ET.SubElement(diagram, f"{{{BPMNDI_NS}}}BPMNPlane", id="BPMNPlane_1", bpmnElement=self.process.id)

        # Generate shapes
        for elem_id, info in self.process.positions.items():
            shape = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", id=f"{elem_id}_di", bpmnElement=elem_id)
            ET.SubElement(shape, f"{{{OMGDC_NS}}}Bounds", **info['coords'])

        # Generate edges
        for flow in self.process.element.findall(f'{{{BPMN_NS}}}sequenceFlow'):
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            source_info = self.process.positions.get(source_ref)
            target_info = self.process.positions.get(target_ref)

            if not source_info or not target_info:
                logging.warning(f"Could not find position info for edge '{flow_id}' (source: '{source_ref}', target: '{target_ref}'). Skipping edge generation.")
                continue

            edge = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNEdge", id=f"{flow_id}_di", bpmnElement=flow_id)
            # Waypoint from source to target
            ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=str(int(source_info['coords']['x']) + int(source_info['coords']['width'])), y=str(int(source_info['coords']['y']) + int(source_info['coords']['height']) // 2))
            ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=target_info['coords']['x'], y=str(int(target_info['coords']['y']) + int(target_info['coords']['height']) // 2))

    def _indent(self, elem, level=0):
        """Recursively indents the XML tree for pretty-printing."""
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
    """Represents a single BPMN process."""
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        """
        Initializes the Process.
        Args:
            id (str): The ID of the process.
            is_executable (bool): Whether the process is executable.
            history_ttl (str): The history time-to-live for Camunda.
        """
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
        """
        Adds a BPMN element to the process and calculates its position.
        Args:
            element (ET.Element): The XML element to add.
            elem_id (str): The ID of the element.
            width (int): The width of the element for diagramming.
            height (int): The height of the element for diagramming.
        """
        self.elements[elem_id] = element
        self.positions[elem_id] = {
            'coords': {'x': str(self._x_pos), 'y': str(self._y_pos), 'width': str(width), 'height': str(height)}
        }
        self._x_pos += width + HORIZONTAL_SPACING

    def add_sequence_flow(self, id, source_ref, target_ref):
        """
        Adds a sequence flow between two elements.
        Args:
            id (str): The ID of the sequence flow.
            source_ref (str): The ID of the source element.
            target_ref (str): The ID of the target element.
        Returns:
            ET.Element: The created sequence flow element.
        """
        return ET.SubElement(self.element, f"{{{BPMN_NS}}}sequenceFlow", id=id, sourceRef=source_ref, targetRef=target_ref)

class StartEvent:
    """A BPMN Start Event."""
    def __init__(self, process, id="StartEvent_1"):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}startEvent", id=id)
        process._add_element(self.element, id, START_EVENT_WIDTH, START_EVENT_HEIGHT)

class EndEvent:
    """A BPMN End Event."""
    def __init__(self, process, id="EndEvent_1"):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}endEvent", id=id)
        process._add_element(self.element, id, END_EVENT_WIDTH, END_EVENT_HEIGHT)

class HumanTask:
    """A BPMN User Task (Human Task)."""
    def __init__(self, process, id, name, meta=None, extension_meta=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}userTask", id=id, name=name, **(meta if meta else {{}}))
        if extension_meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for k, v in extension_meta.items():
                ET.SubElement(ext, f"{{{CAMUNDA_NS}}}meta", key=str(k)).text = str(v)
        process._add_element(self.element, id, TASK_WIDTH, TASK_HEIGHT)

class ConnectorServiceTask:
    """A BPMN Service Task with an HTTP connector."""
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
        process._add_element(self.element, id, TASK_WIDTH, TASK_HEIGHT)

class ScriptTask:
    """A BPMN Script Task."""
    def __init__(self, process, id, name, script_format, script):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}scriptTask", id=id, name=name, **{{f"{{{CAMUNDA_NS}}}scriptFormat": script_format}})
        ET.SubElement(self.element, f"{{{BPMN_NS}}}script").text = script
        process._add_element(self.element, id, TASK_WIDTH, TASK_HEIGHT)

class ExclusiveGateway:
    """A BPMN Exclusive (XOR) Gateway."""
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name: attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", attrib=attribs)
        process._add_element(self.element, id, GATEWAY_WIDTH, GATEWAY_HEIGHT)

class ParallelGateway:
    """A BPMN Parallel Gateway."""
    def __init__(self, process, id, name=None):
        attribs = {"id": id}
        if name: attribs["name"] = name
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}parallelGateway", attrib=attribs)
        process._add_element(self.element, id, GATEWAY_WIDTH, GATEWAY_HEIGHT)

# --- Example Usage ---
if __name__ == "__main__":
    wf = Workflow()
    proc = Process()
    wf.add_process(proc)

    # Create elements
    StartEvent(proc, "StartEvent_1")
    HumanTask(proc, "Task_1", "Human Task", extension_meta={'x': 1, 'y': 2})
    ConnectorServiceTask(proc, "Task_2", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar2"})
    ExclusiveGateway(proc, "Gateway_1", "Decision")
    
    # Branch 1
    task3 = ConnectorServiceTask(proc, "Task_3", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar3"})
    
    # Branch 2 - Repositioning Y
    proc._y_pos += 150
    task4 = ConnectorServiceTask(proc, "Task_4", "REST Service Task", url="http://host.docker.internal:8081", method="POST", payload={"foo": "bar4"})
    proc._y_pos -= 150 # Reset Y position for main flow

    # Merge
    merge_gateway = ParallelGateway(proc, "Gateway_2", "Parallel Split")
    
    ScriptTask(proc, "Task_5", "Script Task", script_format="javascript", script="print('Script Task executed!')")
    EndEvent(proc, "EndEvent_1")

    # Add sequence flows
    proc.add_sequence_flow("Flow_1", "StartEvent_1", "Task_1")
    proc.add_sequence_flow("Flow_2", "Task_1", "Task_2")
    proc.add_sequence_flow("Flow_3", "Task_2", "Gateway_1")
    
    # Flows from gateway to branches
    proc.add_sequence_flow("Flow_4", "Gateway_1", "Task_3")
    proc.add_sequence_flow("Flow_5", "Gateway_1", "Task_4")
    
    # Flows from branches to merge gateway
    proc.add_sequence_flow("Flow_6", "Task_3", "Gateway_2")
    proc.add_sequence_flow("Flow_7", "Task_4", "Gateway_2")

    proc.add_sequence_flow("Flow_8", "Gateway_2", "Task_5")
    proc.add_sequence_flow("Flow_9", "Task_5", "EndEvent_1")

    wf.to_xml("workflow_improved_v3.bpmn")
