from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtWidgets import QRadioButton, QDesktopWidget
from _ui_main_window import Ui_MainWindow
import os
import json
from arinc_handler import ArincWorker
from RS_handler import RsWorker

base_dir = os.path.dirname(os.path.abspath(__file__))

class MainWindow(QtWidgets.QMainWindow):

    sig_run_arinc_handler = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.showFullScreen()

        # Get com-ports names
        with open('ports.json', 'r', encoding='utf-8') as f:
            ports = json.load(f)

        self.arinc_thread = QThread()
        self.arinc_handler = ArincWorker(ports['arinc-com'])
        self.arinc_handler.moveToThread(self.arinc_thread)
        #self.rs_handler = RsWorker(ports['rs-422'])

        #actions
        self.ui.action_exit.triggered.connect(self.on_action_exit_clicked)
        self.ui.action_min.triggered.connect(self.on_action_min_clicked)

        # Signals connection
        self.arinc_handler.sig_error.connect(self.slot_arinc_handler_error)
        self.arinc_handler.sig_connected.connect(self.slot_arinc_handler_connected)
        self.sig_run_arinc_handler.connect(self.arinc_handler.slot_connect)
        self.ui.setDefaultButton.clicked.connect(self.slot_set_default_button)

        #labels
        self.arinc_handler.sig_bus_activity.connect(self.slot_bus_activity)
        self.arinc_handler.sig_352.connect(self.slot_352_word)
        self.arinc_handler.sig_353.connect(self.slot_353_word)
        self.arinc_handler.sig_163.connect(self.slot_163_word)
        self.arinc_handler.sig_057.connect(self.slot_057_word)

        self.arinc_thread.start()
        self.sig_run_arinc_handler.emit()

    def parse_dict_to_radio(self, dict_data):
        for key, value in dict_data.items():
            attr_1, attr_0 = (key + '_1', key + '_0')
            if hasattr(self.ui, attr_1) and hasattr(self.ui, attr_0):
                box_1: QRadioButton = getattr(self.ui, attr_1)
                box_0: QRadioButton = getattr(self.ui, attr_0)
                if value:
                    box_1.setChecked(True)
                else:
                    box_0.setChecked(True)

    @pyqtSlot()
    def on_action_exit_clicked(self):
        exit()

    @pyqtSlot()
    def on_action_min_clicked(self):
        self.showMinimized()

    @pyqtSlot(bool)
    def slot_bus_activity(self, active):
        if active:
            self.ui.sdac_1.setChecked(True)

    @pyqtSlot()
    def slot_set_default_button(self):
        pass

    @pyqtSlot(dict)
    def slot_352_word(self, disc_sig_dict):
        if disc_sig_dict['FAULT_WARN_WR']:
            self.ui.FAULT_WARN_WR_1.setChecked(True)
        else:
            self.ui.FAULT_WARN_WR_0.setChecked(True)

        if disc_sig_dict['SYS_IN_CNTL_IN']:
            self.ui.SYS_IN_CNTL_IN_1.setChecked(True)
        else:
            self.ui.SYS_IN_CNTL_IN_0.setChecked(True)

        if disc_sig_dict['ENG_1_N2']:
            self.ui.ENG1_N2_1.setChecked(True)
        else:
            self.ui.ENG1_N2_0.setChecked(True)

        if disc_sig_dict['ENG_2_N2']:
            self.ui.ENG2_N2_1.setChecked(True)
        else:
            self.ui.ENG2_N2_0.setChecked(True)

        if disc_sig_dict['LDG_GEAR_NORM']:
            self.ui.LDG_GEAR_NORM_1.setChecked(True)
        else:
            self.ui.LDG_GEAR_NORM_0.setChecked(True)

        if disc_sig_dict['LDG_GEAR_ESS']:
            self.ui.LDG_GEAR_ESS_1.setChecked(True)
        else:
            self.ui.LDG_GEAR_ESS_0.setChecked(True)

    @pyqtSlot(dict)
    def slot_353_word(self, disc_sig_dict):
        self.parse_dict_to_radio(disc_sig_dict)

    @pyqtSlot(int)
    def slot_163_word(self, data):
        self.ui.lcdNumber.display(data)

    @pyqtSlot(dict)
    def slot_057_word(self, data):
        if data['sys_in_control']:
            self.ui.sys_in_ctrl_yes.setChecked(True)
        else:
            self.ui.sys_in_ctrl_no.setChecked(True)

        if data['sys_status']:
            self.ui.sys_status_fail.setChecked(True)
        else:
            self.ui.sys_status_good.setChecked(True)

        if data['lfe_from_fms']:
            self.ui.lfe_from_fms_nused.setChecked(True)
        else:
            self.ui.lfe_from_fms_used.setChecked(True)

        if data['excessive_cabin_altitude']:
            self.ui.cabine_altitude_warn.setChecked(True)
        else:
            self.ui.cabine_altitude_nwarn.setChecked(True)

        if data['low_differential_pressure']:
            self.ui.diff_pressure_warn.setChecked(True)
        else:
            self.ui.diff_pressure_nwarn.setChecked(True)

        if data['preplanned_descent_info']:
            self.ui.preplanned_toofast.setChecked(True)
        else:
            self.ui.preplanned_good.setChecked(True)

        if data['lfes_status']:
            self.ui.lfes_stat_manual.setChecked(True)
        else:
            self.ui.lfes_stat_auto.setChecked(True)

        match data['used_adirs_channel']:
            case 0:
                self.ui.adirs_ch_no.setChecked(True)
            case 1:
                self.ui.adirs_ch_1.setChecked(True)
            case 2:
                self.ui.adirs_ch_2.setChecked(True)
            case 3:
                self.ui.adirs_ch_3.setChecked(True)

        if data['fms_enable']:
            self.ui.fms_enable.setChecked(True)
        else:
            self.ui.fms_disable.setChecked(True)


        used_mode = data['flight_modes']
        modes = ['gr', 'to', 'ci', 'ce', 'cr', 'di', 'de', 'ab']
        for i, mode in enumerate(modes):
            widget: QRadioButton = getattr(self.ui, f'flight_modes_{mode}')
            if i == used_mode:
                widget.setChecked(True)

        match data['fms_selection']:
            case 0:
                self.ui.fms_sel_1eng.setChecked(True)
            case 1:
                self.ui.fms_sel_1neng.setChecked(True)
            case 2:
                self.ui.fms_sel_2eng.setChecked(True)
            case 3:
                self.ui.fms_sel_2neng.setChecked(True)

        if data['fms_use']:
            self.ui.fms_use_nuse.setChecked(True)
        else:
            self.ui.fms_use_use.setChecked(True)

        if data['qnh_from_fms']:
            self.ui.qnh_nuse.setChecked(True)
        else:
            self.ui.qnh_use.setChecked(True)

        if data['class_2_fault']:
            self.ui.class2fault_pres.setChecked(True)
        else:
            self.ui.class2fault_npres.setChecked(True)

    @pyqtSlot()
    def slot_arinc_handler_connected(self):
        print('arinc handler connected')

    @pyqtSlot(str)
    def slot_arinc_handler_error(self, error:str):
        print('arinc handler error: ', error)
