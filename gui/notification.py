from PyQt6 import QtWidgets, QtCore, QtGui
from core.utils import apply_stylesheet

def show_notification(parent, message: str, duration: int = 1500):
    """Show a floating notification label with fade-in/out animation over the parent widget."""
    notif = QtWidgets.QLabel(message, parent)
    apply_stylesheet(notif, """
        QLabel {
            background: rgba(30,30,30,220);
            color: white;
            border-radius: 10px;
            padding: 12px 32px;
            font-size: 13pt;
            font-weight: 700;
            min-width: 200px;
            qproperty-alignment: AlignCenter;
            box-shadow: 0 4px 24px rgba(0,0,0,0.18);
        }
    """)
    notif.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.ToolTip)
    notif.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
    notif.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
    notif.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    notif.adjustSize()
    # Center in parent
    geo = parent.geometry()
    notif_geo = notif.frameGeometry()
    x = (geo.width() - notif_geo.width()) // 2
    y = geo.height() - notif_geo.height() - 48
    notif.move(x, y)
    notif.setWindowOpacity(0.0)
    notif.show()
    notif.raise_()
    # Fade in
    anim_in = QtCore.QPropertyAnimation(notif, b"windowOpacity", parent)
    anim_in.setDuration(250)
    anim_in.setStartValue(0.0)
    anim_in.setEndValue(1.0)
    def start_fade_out():
        anim_out = QtCore.QPropertyAnimation(notif, b"windowOpacity", parent)
        anim_out.setDuration(600)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.finished.connect(notif.close)
        anim_out.start()
    anim_in.finished.connect(lambda: QtCore.QTimer.singleShot(duration, start_fade_out))
    anim_in.start()
