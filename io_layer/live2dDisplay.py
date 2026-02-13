import os.path
import sys

"""
Live2D model display without fade in/out effect
"""

import live2d.v3 as live2d
# import live2d.v2 as live2d
import math
import os
import resources
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QOpenGLWidget



class Live2DCanvas(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model: None | live2d.LAppModel = None

        # 设置窗口属性
        self.setWindowTitle("Live2DCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 隐藏头部栏
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 确保窗口边缘透明
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # 鼠标拖动相关变量
        self.is_dragging = False
        self.drag_start_position = None

    def initializeGL(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        if live2d.LIVE2D_VERSION == 3:
            self.model.LoadModelJson(os.path.join(resources.RESOURCES_DIRECTORY, "v3", "YZL10/乐正绫10live2d.model3.json"))
        else:
            self.model.LoadModelJson(os.path.join(resources.RESOURCES_DIRECTORY, "v2", "kasumi2/kasumi2.model.json"))
        
        # 移除canvas创建，不再使用

        self.startTimer(int(1000 / 120))
    
    def timerEvent(self,a0):
        # 移除渐入渐出效果，只保留更新
        self.update()

    def on_draw(self):
        live2d.clearBuffer()
        self.model.Draw()

    def paintGL(self):
        self.model.Update()
        
        # 直接绘制，移除canvas使用
        self.on_draw()

    def resizeGL(self, width: int, height: int):
        self.model.Resize(width, height)
    
    def mousePressEvent(self, event):
        # 处理鼠标按下事件，开始拖动
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        # 处理鼠标移动事件，执行拖动
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_start_position)
    
    def mouseReleaseEvent(self, event):
        # 处理鼠标释放事件，结束拖动
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_start_position = None


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    live2d.init()
    app = QApplication(sys.argv)
    win = Live2DCanvas()
    win.show()
    app.exec()
    live2d.dispose()
