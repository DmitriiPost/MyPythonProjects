import json
import sys
import os
import random
import xml.etree.ElementTree as ET
from math import atan2, sin, cos
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QDialog, QLineEdit,
    QLabel, QHBoxLayout, QMessageBox, QComboBox, QFormLayout, QGraphicsScene, QGraphicsView,
    QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsTextItem,
    QMenu, QColorDialog, QDialogButtonBox, QGraphicsPolygonItem, QAction, QFileDialog, QInputDialog
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint
from PyQt5.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QFont, QBrush,
    QTransform, QPolygonF
)

# Константы для стилей соединений
LINE_STYLE_STRAIGHT = 0
LINE_STYLE_POLYLINE = 1
LINE_STYLE_CURVE = 2

END_STYLE_NONE = 0
END_STYLE_ARROW = 1
END_STYLE_CIRCLE = 2
END_STYLE_SQUARE = 3

class ConnectionStyleDialog(QDialog):
    def __init__(self, connection=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка соединения")
        self.connection = connection
        
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        layout.addRow("Название:", self.name_edit)
        
        self.color_button = QPushButton("Выбрать цвет")
        self.color_button.clicked.connect(self.choose_color)
        self.current_color = QColor(Qt.black)
        layout.addRow("Цвет линии:", self.color_button)
        
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItem("Прямая", LINE_STYLE_STRAIGHT)
        self.line_style_combo.addItem("Ломаная", LINE_STYLE_POLYLINE)
        self.line_style_combo.addItem("Кривая", LINE_STYLE_CURVE)
        layout.addRow("Стиль линии:", self.line_style_combo)
        
        self.start_style_combo = QComboBox()
        self.start_style_combo.addItem("Нет", END_STYLE_NONE)
        self.start_style_combo.addItem("Стрелка", END_STYLE_ARROW)
        self.start_style_combo.addItem("Кружок", END_STYLE_CIRCLE)
        self.start_style_combo.addItem("Квадрат", END_STYLE_SQUARE)
        layout.addRow("Стиль начала:", self.start_style_combo)
        
        self.end_style_combo = QComboBox()
        self.end_style_combo.addItem("Нет", END_STYLE_NONE)
        self.end_style_combo.addItem("Стрелка", END_STYLE_ARROW)
        self.end_style_combo.addItem("Кружок", END_STYLE_CIRCLE)
        self.end_style_combo.addItem("Квадрат", END_STYLE_SQUARE)
        layout.addRow("Стиль конца:", self.end_style_combo)
        
        self.width_spin = QLineEdit("2")
        layout.addRow("Толщина линии:", self.width_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
        if connection:
            self.name_edit.setText(connection.name)
            self.current_color = connection.pen().color()
            self.line_style_combo.setCurrentIndex(connection.line_style)
            self.start_style_combo.setCurrentIndex(connection.start_style)
            self.end_style_combo.setCurrentIndex(connection.end_style)
            self.width_spin.setText(str(connection.pen().width()))
    
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
    
    def get_style(self):
        return {
            'name': self.name_edit.text(),
            'color': self.current_color.name(),
            'line_style': self.line_style_combo.currentData(),
            'start_style': self.start_style_combo.currentData(),
            'end_style': self.end_style_combo.currentData(),
            'width': int(self.width_spin.text())
        }

class PortItem(QGraphicsEllipseItem):
    def __init__(self, port_type, pos, size, parent, port_index):
        super().__init__(-size//2, -size//2, size, size, parent)
        self.port_type = port_type
        self.size = size
        self.port_index = port_index
        self.parent_name = parent.name  # Сохраняем имя родительского оборудования
        self.unique_id = f"{self.parent_name}_{port_type}_{port_index}"  # Уникальный идентификатор
        
        self.setBrush(QBrush(QColor(hash(self.unique_id) % 256,
                           hash(self.unique_id + "1") % 256,
                           hash(self.unique_id + "2") % 256)))
        
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CrossCursor)
        self.label = None

    def contextMenuEvent(self, event):
        scene = self.scene()
        if not scene or not hasattr(scene, 'get_connections_for_port'):
            return

        connections = scene.get_connections_for_port(self)
        if not connections:
            return

        menu = QMenu()
        delete_action = menu.addAction("Удалить соединение")
        action = menu.exec_(event.screenPos())

        if action == delete_action:
            for conn in connections:
                scene.delete_connection(conn)

    def shape(self):
        path = super().shape()
        path.addEllipse(self.rect().adjusted(-5, -5, 5, 5))
        return path

    def add_label_to_scene(self, scene):
        self.label = QGraphicsTextItem(self.port_type)
        self.label.setZValue(200)
        self.label.setDefaultTextColor(Qt.darkBlue)
        scene.addItem(self.label)
        self.update_label_position()

    def update_label_position(self):
        if not self.label:
            return
        port_pos = self.scenePos()
        label_width = self.label.boundingRect().width()
        label_height = self.label.boundingRect().height()
        offset_y = -label_height / 2
        if self.port_index % 2 == 0:
            self.label.setPos(port_pos.x() - 10 - label_width, port_pos.y() + offset_y)
        else:
            self.label.setPos(port_pos.x() + 10, port_pos.y() + offset_y)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(Qt.yellow))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        color = QColor(hash(self.port_type) % 256,
                     hash(self.port_type + "1") % 256,
                     hash(self.port_type + "2") % 256)
        self.setBrush(QBrush(color))
        super().hoverLeaveEvent(event)

    def update_connections(self):
        scene = self.scene()
        if scene and hasattr(scene, 'update_connections_for_port'):
            scene.update_connections_for_port(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            self.update_connections()
            self.update_label_position()
        return super().itemChange(change, value)

class EquipmentItem(QGraphicsRectItem):
    def __init__(self, rect, name, eq_type, ports, parent=None):
        super().__init__(rect, parent)
        self.name = name
        self.eq_type = eq_type
        self.ports = ports
        self.port_size = 10

        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen(Qt.black, 2))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(0)

        self.text = f"{name} ({eq_type})"

        self.port_items = []
        for i, port in enumerate(ports):
            port_pos = self.get_port_position(i, len(ports))
            port_item = PortItem(port['type'], port_pos, self.port_size, self, i)
            port_item.setPos(port_pos)
            self.port_items.append(port_item)

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Удалить оборудование")
        action = menu.exec_(event.screenPos())

        if action == delete_action:
            scene = self.scene()
            if scene and hasattr(scene, 'delete_equipment_item'):
                scene.delete_equipment_item(self)

    def add_labels_to_scene(self, scene):
        for port in self.port_items:
            port.add_label_to_scene(scene)
#поискать, где индекс
    def get_port_position(self, port_index, total_ports):
        rect = self.rect()
        port_side = port_index % 2
        pos_on_side = (port_index // 2) + 1
        ports_per_side = (total_ports + 1) // 2

        if port_side == 0:
            x = rect.left() - self.port_size // 2
            y = rect.top() + rect.height() * pos_on_side // (ports_per_side + 1)
        else:
            x = rect.right() + self.port_size // 2
            y = rect.top() + rect.height() * pos_on_side // (ports_per_side + 1)

        return QPointF(x, y)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setFont(QFont("Arial", 8))
        text_rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, self.text)

class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_port, end_port, style=None):
        super().__init__()
        self.start_port = start_port
        self.end_port = end_port
        
        self.name = ""
        self.line_style = LINE_STYLE_CURVE
        self.start_style = END_STYLE_NONE
        self.end_style = END_STYLE_ARROW
        self.width = 2
        self.color = QColor(Qt.black)
        
        if style:
            self.apply_style(style)
        
        self.setZValue(10)
        self.update_path()
    
    def apply_style(self, style):
        self.name = style.get('name', "")
        self.line_style = style.get('line_style', LINE_STYLE_CURVE)
        self.start_style = style.get('start_style', END_STYLE_NONE)
        self.end_style = style.get('end_style', END_STYLE_ARROW)
        self.width = style.get('width', 2)
        self.color = QColor(style.get('color', Qt.black))
        
        pen = QPen(self.color, self.width)
        self.setPen(pen)
    
    def update_path(self):
        path = QPainterPath()
        start = self.start_port.scenePos()
        end = self.end_port.scenePos()

        path.moveTo(start)
        
        if self.line_style == LINE_STYLE_STRAIGHT:
            path.lineTo(end)
        elif self.line_style == LINE_STYLE_POLYLINE:
            mid_x = (start.x() + end.x()) / 2
            path.lineTo(mid_x, start.y())
            path.lineTo(mid_x, end.y())
            path.lineTo(end)
        else:  # LINE_STYLE_CURVE
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            
            if abs(dx) > abs(dy):  # Горизонтальное соединение
                ctrl1 = QPointF(start.x() + dx * 0.25, start.y())
                ctrl2 = QPointF(end.x() - dx * 0.25, end.y())
            else:  # Вертикальное соединение
                ctrl1 = QPointF(start.x(), start.y() + dy * 0.25)
                ctrl2 = QPointF(end.x(), end.y() - dy * 0.25)
            
            path.cubicTo(ctrl1, ctrl2, end)
        
        self.setPath(path)
        
        # Удаляем старые окончания
        for item in self.childItems():
            if isinstance(item, (QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem)):
                if item.scene():
                    self.scene().removeItem(item)
                item.setParentItem(None)
        
        # Добавляем новые окончания
        self.draw_end_style(start, end, self.start_style, True)
        self.draw_end_style(end, start, self.end_style, False)

    def draw_end_style(self, pos, opposite_pos, style, is_start):
        if style == END_STYLE_NONE:
            return
        
        # Вычисляем реальное направление линии
        path = self.path()
        if path.isEmpty():
            return
            
        t = 0.99 if not is_start else 0.01
        p1 = path.pointAtPercent(t)
        p2 = path.pointAtPercent(1.0 if not is_start else 0.0)
        
        direction = p2 - p1
        if direction.x() == 0 and direction.y() == 0:
            direction = pos - opposite_pos
        
        length = (direction.x()**2 + direction.y()**2)**0.5
        if length > 0:
            direction = QPointF(direction.x() / length, direction.y() / length)
        else:
            return
        
        size = self.pen().width() * 3
        
        if style == END_STYLE_ARROW:
            arrow_size = QPointF(size * 2, size * 2)
            
            angle = atan2(-direction.y(), direction.x())
            arrow_p1 = pos - direction * arrow_size.x() + QPointF(
                -arrow_size.y() * 0.5 * sin(angle),
                -arrow_size.y() * 0.5 * cos(angle)
            )
            arrow_p2 = pos - direction * arrow_size.x() + QPointF(
                arrow_size.y() * 0.5 * sin(angle),
                arrow_size.y() * 0.5 * cos(angle)
            )
            
            arrow_head = QPolygonF([pos, arrow_p1, arrow_p2])
            arrow = QGraphicsPolygonItem(arrow_head, self)
            arrow.setBrush(QBrush(self.color))
            arrow.setPen(QPen(Qt.NoPen))
        
        elif style == END_STYLE_CIRCLE:
            circle = QGraphicsEllipseItem(-size/2, -size/2, size, size, self)
            circle.setPos(pos)
            circle.setBrush(QBrush(self.color))
            circle.setPen(QPen(Qt.NoPen))
        
        elif style == END_STYLE_SQUARE:
            square = QGraphicsRectItem(-size/2, -size/2, size, size, self)
            square.setPos(pos)
            square.setBrush(QBrush(self.color))
            square.setPen(QPen(Qt.NoPen))
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        style_action = menu.addAction("Изменить стиль")
        delete_action = menu.addAction("Удалить соединение")
        
        action = menu.exec_(event.screenPos())
        
        if action == style_action:
            self.edit_style()
        elif action == delete_action:
            scene = self.scene()
            if scene and hasattr(scene, 'delete_connection'):
                scene.delete_connection(self)
    
    def edit_style(self):
        style = {
            'name': self.name,
            'color': self.color.name(),
            'line_style': self.line_style,
            'start_style': self.start_style,
            'end_style': self.end_style,
            'width': self.width
        }
        
        dialog = ConnectionStyleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_style = dialog.get_style()
            self.apply_style(new_style)
            self.update_path()
            scene = self.scene()
            if scene and hasattr(scene, 'save_schema'):
                scene.save_schema()

class EquipmentView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setInteractive(True)

class EquipmentTypeDialog(QDialog):
    def __init__(self, schema_path):
        super().__init__()
        self.setWindowTitle("Создание типа оборудования")
        self.schema_path = schema_path
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.ports_input = QLineEdit()
        layout.addWidget(QLabel("Наименование оборудования:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Порты (пример: HDMI VGA):"))
        layout.addWidget(self.ports_input)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_type)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_type(self):
        name = self.name_input.text().strip()
        ports = self.ports_input.text().strip().split()

        if not name or not ports:
            QMessageBox.warning(self, "Ошибка", "Введите все данные.")
            return

        root = ET.Element("equipment_type")
        ET.SubElement(root, "name").text = name
        ports_elem = ET.SubElement(root, "ports")
        for port in ports:
            ET.SubElement(ports_elem, "port").text = port

        types_dir = os.path.join(self.schema_path, "equipment_types")
        os.makedirs(types_dir, exist_ok=True)
        filename = os.path.join(types_dir, f"{name}.xml")
        
        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

        self.accept()

class EquipmentInstanceDialog(QDialog):
    def __init__(self, scene, schema_path):
        super().__init__()
        self.setWindowTitle("Создание экземпляра оборудования")
        self.scene = scene
        self.schema_path = schema_path

        self.equipment_types = self.load_types()
        layout = QVBoxLayout()

        self.type_selector = QComboBox()
        for t in self.equipment_types:
            self.type_selector.addItem(t)
        layout.addWidget(QLabel("Выберите тип оборудования:"))
        layout.addWidget(self.type_selector)

        self.ok_button = QPushButton("Продолжить")
        self.ok_button.clicked.connect(self.go_next)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def load_types(self):
        types_dir = os.path.join(self.schema_path, "equipment_types")
        if not os.path.exists(types_dir):
            return []

        types = []
        for filename in os.listdir(types_dir):
            if filename.endswith(".xml"):
                try:
                    tree = ET.parse(os.path.join(types_dir, filename))
                    root = tree.getroot()
                    name = root.find("name").text
                    types.append(name)
                except Exception as e:
                    print(f"Ошибка при загрузке типа {filename}: {e}")
        return types

    def go_next(self):
        selected_type = self.type_selector.currentText()
        if not selected_type:
            QMessageBox.warning(self, "Ошибка", "Выберите тип.")
            return

        types_dir = os.path.join(self.schema_path, "equipment_types")
        filename = os.path.join(types_dir, f"{selected_type}.xml")
        
        ports = []
        try:
            tree = ET.parse(filename)
            root = tree.getroot()
            for port in root.find("ports"):
                ports.append({'type': port.text})
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить тип оборудования: {e}")
            return

        self.close()
        PortsEntryDialog(self.scene, selected_type, ports).exec_()

class PortsEntryDialog(QDialog):
    def __init__(self, scene, eq_type, ports):
        super().__init__()
        self.setWindowTitle("Создание экземпляра")
        self.scene = scene
        self.eq_type = eq_type
        self.ports = ports

        layout = QFormLayout()
        self.name_input = QLineEdit()
        layout.addRow(QLabel("Название устройства:"), self.name_input)

        self.save_button = QPushButton("Создать")
        self.save_button.clicked.connect(self.create_instance)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def create_instance(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название.")
            return

        self.scene.add_equipment_instance(name, self.eq_type, self.ports)
        self.accept()

class EquipmentScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connections = []
        self.temp_connection = None
        self.connection_start = None
        self.port_size = 10
        self.schema_path = None

    def load_schema(self, schema_path):
        self.schema_path = schema_path
        schema_file = os.path.join(schema_path, os.path.basename(schema_path) + ".json")
        
        if not os.path.exists(schema_file):
            return

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = json.load(f)

            self.clear()
            self.connections = []
            
            # Загрузка экземпляров оборудования
            for instance in schema.get("instances", []):
                name = instance['name']
                eq_type = instance['type']
                ports = instance['ports']
                x = instance.get('x', random.randint(50, 500))
                y = instance.get('y', random.randint(50, 400))

                rect = QRectF(0, 0, 160, 110)
                self.add_equipment_instance(name, eq_type, ports, rect, QPointF(x, y))

            # Создаем словарь всех портов по их unique_id
            port_dict = {}
            for item in self.items():
                if isinstance(item, EquipmentItem):
                    for port in item.port_items:
                        port_dict[port.unique_id] = port

            # Загрузка соединений
            for connection in schema.get("connections", []):
                try:
                    # Пробуем загрузить по новому формату (с unique_id)
                    if 'from_port_id' in connection and 'to_port_id' in connection:
                        start_port = port_dict[connection['from_port_id']]
                        end_port = port_dict[connection['to_port_id']]
                    else:
                        # Fallback для старых схем (загрузка по индексам)
                        from_item = next((item for item in self.items() 
                                        if isinstance(item, EquipmentItem) and 
                                        item.name == connection['from']), None)
                        to_item = next((item for item in self.items() 
                                    if isinstance(item, EquipmentItem) and 
                                    item.name == connection['to']), None)
                        
                        if from_item and to_item:
                            from_ports = [p for p in from_item.port_items 
                                        if p.port_type == connection['from_port']]
                            to_ports = [p for p in to_item.port_items 
                                    if p.port_type == connection['to_port']]
                            
                            from_port_idx = connection.get('from_port_index', 0)
                            to_port_idx = connection.get('to_port_index', 0)
                            
                            if from_port_idx < len(from_ports) and to_port_idx < len(to_ports):
                                start_port = from_ports[from_port_idx]
                                end_port = to_ports[to_port_idx]

                    # Проверяем, что порты не заняты
                    if (start_port and end_port and
                        not any(conn.start_port == start_port or conn.end_port == start_port 
                            for conn in self.connections) and
                        not any(conn.start_port == end_port or conn.end_port == end_port 
                            for conn in self.connections)):
                        self.add_connection(start_port, end_port, connection.get('style'))
                        
                except Exception as e:
                    print(f"Ошибка загрузки соединения: {e}")

        except Exception as e:
            print("Ошибка при загрузке схемы:", e)

    def save_schema(self):
        if not self.schema_path:
            return False
            
        schema_file = os.path.join(self.schema_path, os.path.basename(self.schema_path) + ".json")
        schema = {
            "instances": [],
            "connections": []
        }

        # Сохраняем экземпляры оборудования
        for item in self.items():
            if isinstance(item, EquipmentItem):
                pos = item.pos()
                schema["instances"].append({
                    'name': item.name,
                    'type': item.eq_type,
                    'ports': item.ports,
                    'x': pos.x(),
                    'y': pos.y()
                })

        # Сохраняем соединения с уникальными ID портов
        for conn in self.connections:
            start_eq = conn.start_port.parentItem()
            end_eq = conn.end_port.parentItem()
            
            connection_data = {
                'from': start_eq.name,
                'to': end_eq.name,
                'from_port_id': conn.start_port.unique_id,  # Используем unique_id
                'to_port_id': conn.end_port.unique_id,
                'style': {
                    'name': conn.name,
                    'color': conn.color.name(),
                    'line_style': conn.line_style,
                    'start_style': conn.start_style,
                    'end_style': conn.end_style,
                    'width': conn.width
                }
            }
            schema["connections"].append(connection_data)

        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        
        return True

    def delete_equipment_item(self, equipment):
        connections_to_delete = []
        for conn in self.connections:
            start_eq = conn.start_port.parentItem()
            end_eq = conn.end_port.parentItem()
            if start_eq == equipment or end_eq == equipment:
                connections_to_delete.append(conn)

        for conn in connections_to_delete:
            self.delete_connection(conn)

        for port in equipment.port_items:
            if port.label:
                self.removeItem(port.label)

        self.removeItem(equipment)
        self.save_schema()

    def delete_connection(self, connection):
        if connection in self.connections:
            self.removeItem(connection)
            self.connections.remove(connection)
            self.save_schema()

    def get_connections_for_port(self, port):
        return [conn for conn in self.connections
                if conn.start_port == port or conn.end_port == port]

    def add_equipment_instance(self, name, eq_type, ports, rect=None, pos=None):
        if rect is None:
            rect = QRectF(0, 0, 160, 110)

        if pos is None:
            pos = QPointF(random.randint(50, 500), random.randint(50, 400))

        item = EquipmentItem(rect, name, eq_type, ports)
        item.setPos(pos)
        self.addItem(item)
        item.add_labels_to_scene(self)
        self.save_schema()

    def add_connection(self, start_port, end_port, style=None):
        # Проверка на соединение с самим собой
        if start_port.parentItem() == end_port.parentItem():
            QMessageBox.warning(None, "Ошибка", "Нельзя соединять порты одного устройства!")
            return

        # Проверка на уже существующее соединение между устройствами
        for conn in self.connections:
            conn_devices = {conn.start_port.parentItem(), conn.end_port.parentItem()}
            current_devices = {start_port.parentItem(), end_port.parentItem()}
            if conn_devices == current_devices:
                QMessageBox.warning(None, "Ошибка", "Эти устройства уже соединены!")
                return

        # Проверка занятости конкретных портов
        if any(conn.start_port == start_port or conn.end_port == start_port 
            for conn in self.connections):
            QMessageBox.warning(None, "Ошибка", f"Порт {start_port.port_type} уже используется!")
            return
            
        if any(conn.start_port == end_port or conn.end_port == end_port 
            for conn in self.connections):
            QMessageBox.warning(None, "Ошибка", f"Порт {end_port.port_type} уже используется!")
            return

        # Создаем соединение
        connection = ConnectionItem(start_port, end_port, style)
        self.addItem(connection)

        if style is None:
            dialog = ConnectionStyleDialog()
            if dialog.exec_() == QDialog.Accepted:
                connection.apply_style(dialog.get_style())
                connection.update_path()
            else:
                self.removeItem(connection)
                return

        self.connections.append(connection)
        self.save_schema()

    def update_connections_for_port(self, port):
        for conn in self.connections:
            if conn.start_port == port or conn.end_port == port:
                conn.update_path()

    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        if event.button() == Qt.LeftButton and isinstance(item, PortItem):
            self.connection_start = item
            self.temp_connection = QGraphicsPathItem()
            self.temp_connection.setPen(QPen(Qt.red, 2, Qt.DashLine))
            self.temp_connection.setZValue(1000)

            start_pos = item.scenePos()
            path = QPainterPath()
            path.moveTo(start_pos)
            self.temp_connection.setPath(path)

            self.addItem(self.temp_connection)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.connection_start and self.temp_connection:
            start_pos = self.connection_start.scenePos()
            end_pos = event.scenePos()

            path = QPainterPath()
            path.moveTo(start_pos)

            dx = end_pos.x() - start_pos.x()
            dy = end_pos.y() - start_pos.y()

            ctrl_dist = min(abs(dx), abs(dy)) * 0.5
            if abs(dx) > abs(dy):
                ctrl1 = QPointF(start_pos.x() + ctrl_dist, start_pos.y())
                ctrl2 = QPointF(end_pos.x() - ctrl_dist, end_pos.y())
            else:
                ctrl1 = QPointF(start_pos.x(), start_pos.y() + ctrl_dist)
                ctrl2 = QPointF(end_pos.x(), end_pos.y() - ctrl_dist)

            path.cubicTo(ctrl1, ctrl2, end_pos)
            self.temp_connection.setPath(path)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.connection_start and event.button() == Qt.LeftButton:
            items = self.items(event.scenePos())
            end_port = None

            for item in items:
                if isinstance(item, PortItem):
                    end_port = item
                    break

            if end_port and end_port != self.connection_start:
                if end_port.port_type == self.connection_start.port_type:
                    self.add_connection(self.connection_start, end_port)
                else:
                    QMessageBox.warning(None, "Ошибка",
                                    "Можно соединять только порты одного типа!")

            if self.temp_connection:
                self.removeItem(self.temp_connection)
                self.temp_connection = None

            self.connection_start = None
            return

        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Создание и соединение оборудования")
        self.setGeometry(100, 100, 1000, 700)
        self.current_schema_path = None
        
        self.create_scene_and_view()
        self.create_bottom_buttons()
        self.prompt_for_schema_action()
        
    def create_scene_and_view(self):
        self.scene = EquipmentScene()
        self.view = EquipmentView(self.scene)
        self.setCentralWidget(self.view)
    
    def create_bottom_buttons(self):
        self.bottom_layout = QVBoxLayout()
        self.type_button = QPushButton("Создать тип оборудования")
        self.instance_button = QPushButton("Создать экземпляр оборудования")

        self.type_button.clicked.connect(self.add_equipment_type)
        self.instance_button.clicked.connect(self.create_instance)

        self.bottom_layout.addWidget(self.type_button)
        self.bottom_layout.addWidget(self.instance_button)

        bottom_widget = QWidget()
        bottom_widget.setLayout(self.bottom_layout)
        self.setMenuWidget(bottom_widget)
    
    def prompt_for_schema_action(self):
        reply = QMessageBox.question(
            self, 
            'Выбор действия',
            'Хотите создать новую схему (Да) или открыть существующую (Нет)?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.new_schema()
        elif reply == QMessageBox.No:
            self.open_schema()
    
    def new_schema(self):
        filename, ok = QInputDialog.getText(
            self, 'Новая схема',
            'Введите имя для новой схемы (без расширения):'
        )
        
        if ok and filename:
            self.current_schema_path = os.path.join("schemas", filename)
            os.makedirs(self.current_schema_path, exist_ok=True)
            os.makedirs(os.path.join(self.current_schema_path, "equipment_types"), exist_ok=True)
            
            self.scene.clear()
            self.scene.connections = []
            self.scene.schema_path = self.current_schema_path
            
            # Создаем пустую схему
            schema_file = os.path.join(self.current_schema_path, f"{filename}.json")
            with open(schema_file, 'w') as f:
                json.dump({"instances": [], "connections": []}, f)
            
            self.setWindowTitle(f"Схема оборудования - {filename}")
            
            # Создаем пример типа оборудования
            self.create_sample_equipment_type()
    
    def create_sample_equipment_type(self):
        sample_type = os.path.join(self.current_schema_path, "equipment_types", "Sample.xml")
        if not os.path.exists(sample_type):
            root = ET.Element("equipment_type")
            ET.SubElement(root, "name").text = "Sample"
            ports = ET.SubElement(root, "ports")
            ET.SubElement(ports, "port").text = "Port1"
            ET.SubElement(ports, "port").text = "Port2"
            
            tree = ET.ElementTree(root)
            tree.write(sample_type, encoding="utf-8", xml_declaration=True)
    
    def open_schema(self):
        options = QFileDialog.Options()
        schema_dir = QFileDialog.getExistingDirectory(
            self, "Открыть схему", "schemas", options=options)
        
        if schema_dir:
            self.current_schema_path = schema_dir
            self.scene.clear()
            self.scene.connections = []
            self.scene.load_schema(schema_dir)
            
            base_name = os.path.basename(schema_dir)
            self.setWindowTitle(f"Схема оборудования - {base_name}")
    
    def save_schema(self):
        if not self.current_schema_path:
            self.save_schema_as()
            return
            
        if self.scene.save_schema():
            QMessageBox.information(self, 'Сохранено', 'Схема успешно сохранена!')
    
    def save_schema_as(self):
        options = QFileDialog.Options()
        schema_dir = QFileDialog.getExistingDirectory(
            self, "Сохранить схему как", "schemas", options=options)
        
        if schema_dir:
            self.current_schema_path = schema_dir
            self.save_schema()
            
            base_name = os.path.basename(schema_dir)
            self.setWindowTitle(f"Схема оборудования - {base_name}")
    
    def add_equipment_type(self):
        if not self.current_schema_path:
            QMessageBox.warning(self, 'Ошибка', 'Сначала создайте или откройте схему!')
            return
            
        dialog = EquipmentTypeDialog(self.current_schema_path)
        dialog.exec_()
    
    def create_instance(self):
        if not self.current_schema_path:
            QMessageBox.warning(self, 'Ошибка', 'Сначала создайте или откройте схему!')
            return
            
        dialog = EquipmentInstanceDialog(self.scene, self.current_schema_path)
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    os.makedirs("schemas", exist_ok=True)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())