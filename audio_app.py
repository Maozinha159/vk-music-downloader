# -*- coding: utf-8 -*-
"""
  Copyright (C) 2018 Adrian Polyakov

  This file is part of VkMusic Downloader

  VkMusic Downloader free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program. If not, see http://www.gnu.org/licenses/
"""
import codecs
from PyQt5 import QtWidgets
from PyQt5.QtCore import QSizeF, QUrl, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
import audio_gui
from audio_threads import DownloadAudio, GetAudioListThread
from datetime import timedelta
from random import choice


# noinspection PyCallByClass,PyTypeChecker,PyArgumentList
class VkAudioApp(QtWidgets.QMainWindow, audio_gui.Ui_MainWindow):
    def __init__(self, info, config, cookie):
        super().__init__()
        self.setupUi(self)
        self.statusBar()

        self.config = config

        self.btnConfirm.clicked.connect(self.start)
        self.search.textChanged.connect(self.search_tracks)

        self.saveAll = QtWidgets.QAction(QIcon('save_all.png'), '&Сохранить', self)
        self.saveAll.setStatusTip('Сохранить список аудиозаписей в файл со ссылками для их скачивания')
        self.saveAll.setShortcut('Ctrl+S')
        self.saveAll.setEnabled(False)
        self.saveAll.triggered.connect(self.save_all)

        self.saveWithoutLinks = QtWidgets.QAction(QIcon('save_without_links.png'), '&Сохранить без ссылок', self)
        self.saveWithoutLinks.setStatusTip('Сохранить список аудиозаписей в файл без ссылок для их скачивания')
        self.saveWithoutLinks.setShortcut('Ctrl+Shift+S')
        self.saveWithoutLinks.setEnabled(False)
        self.saveWithoutLinks.triggered.connect(self.save_without_links)

        self.downloadAll = QtWidgets.QAction(QIcon('download_all.png'), '&Скачать всё', self)
        self.downloadAll.setStatusTip('Скачать все аудиозаписи из списка ниже')
        self.downloadAll.setShortcut('Ctrl+D')
        self.downloadAll.setEnabled(False)
        self.downloadAll.triggered.connect(self.download_all)

        self.downloadSelected = QtWidgets.QAction(QIcon('download_selected.png'), '&Скачать выбранное', self)
        self.downloadSelected.setStatusTip('Скачать выбранные ауиозаписи из списка ниже')
        self.downloadSelected.setShortcut('Ctrl+Shift+D')
        self.downloadSelected.setEnabled(False)
        self.downloadSelected.triggered.connect(self.download_selected)

        self.luckyMe = QtWidgets.QAction(QIcon('lucky_me.png'), '&Мне повёзет', self)
        self.luckyMe.setStatusTip('Воспроизвести случайную аудиозапись из списка')
        self.luckyMe.setShortcut('Ctrl+L')
        self.luckyMe.setEnabled(False)
        self.luckyMe.triggered.connect(self.play_track)

        menu_bar = self.menuBar()
        music_menu = menu_bar.addMenu('&Музыка')
        music_menu.addAction(self.saveAll)
        music_menu.addAction(self.saveWithoutLinks)
        music_menu.addAction(self.downloadAll)
        music_menu.addAction(self.downloadSelected)
        music_menu.addAction(self.luckyMe)

        self.trackList.itemDoubleClicked.connect(self.play_track)
        self.trackList.itemExpanded.connect(self.on_item_expanded)

        self.get_audio = GetAudioListThread(cookie, self)
        self.get_audio.signal.connect(self.finished)
        self.get_audio.str_signal.connect(self.auth_handler)

        self.download_audio = DownloadAudio()
        self.download_audio.signal.connect(self.done)
        self.download_audio.int_signal.connect(lambda x: self.progressBar.setValue(x))

        video_item = QGraphicsVideoItem()
        self.current_volume = 100
        video_item.setSize(QSizeF(1, 1))
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(video_item)
        self.mediaPlayer.stateChanged.connect(lambda x: [self.toggle_buttons(True), self.toggle_fields(True)])
        self.mediaPlayer.positionChanged.connect(lambda x: self.statusBar().showMessage(
            'Воспроизводится {}: {} / {} Громкость: {}'.format(self.selected[0].text(0), timedelta(milliseconds=x),
                                                               timedelta(milliseconds=self.mediaPlayer.duration()),
                                                               self.current_volume)))

        if info:
            self.login.setText(info[0])
            self.password.setText(info[1])
            self.user_link.setText(info[2])

        self.hidden_tracks = []
        self.selected = None
        self.tracks = None
        self.string = None
        self.albums = None
        self.key = None

    def auth_handler(self, result):
        self.key = None
        num, ok = QtWidgets.QInputDialog.getText(self, 'Двухфакторная аутентификация', result)
        if ok:
            self.key = num

    def start(self):
        self.hidden_tracks.clear()
        if self.saveData.isChecked():
            with open(self.config, 'wb') as d:
                data = self.login.text() + '|' + self.password.text() + '|' + self.user_link.text()
                data_crypted = codecs.encode(bytes(data, 'utf-8'), 'hex')
                d.write(data_crypted)
        self.get_audio.login = self.login.text()
        self.get_audio.password = self.password.text()
        self.get_audio.user_link = self.user_link.text()
        self.get_audio.statusInfo = self.statusInfo
        self.toggle_buttons(False)
        self.trackList.clear()
        self.statusInfo.setText('Процесс получение аудиозаписей начался.\n')
        self.get_audio.start()

    def finished(self, result):
        if result and isinstance(result, tuple):
            self.tracks = result[0]
            self.string = result[1]
            self.albums = result[2]
            self.statusInfo.setText('Список аудиозаписей получен.'
                                    ' Зажмите Ctrl для множественного выбора'
                                    '\n{}, {} шт.'.format(self.string, len(self.tracks)))
            self.trackList.setEnabled(True)
            self.toggle_buttons(True)
            self.luckyMe.setEnabled(True)
            for track in self.tracks:
                self.trackList.addTopLevelItem(
                    QtWidgets.QTreeWidgetItem(self.trackList, ['%(artist)s — %(title)s' % track]))
            for album in self.albums:
                root = QtWidgets.QTreeWidgetItem(self.trackList, [album['title']])
                root.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
                root.setFlags(Qt.ItemIsEnabled)
                self.trackList.addTopLevelItem(root)

        elif isinstance(result, str):
            self.btnConfirm.setEnabled(True)
            self.statusInfo.setText('<html><head/><body><p><span style=" color:#ff0000;">Ошибка: {}'
                                    '</span></p></body></html>'.format(result))

    def save_all(self):
        directory = QtWidgets.QFileDialog.getSaveFileName(self, 'Сохранить как', filter='Text files (*.txt)')[0]
        if not directory.endswith('.txt'):
            directory += '.txt'
        if directory and self.tracks and self.string:
            with open(directory, 'w', encoding='utf-8') as d:
                print('{}, {} шт.\n'.format(self.string, len(self.tracks)), file=d)
                for track in self.tracks:
                    print('%(artist)s - %(title)s: %(link)s\n' % track, file=d)
            self.statusInfo.setText('Список аудиозаписей сохранен в файл {}'.format(directory))

    def save_without_links(self):
        directory = QtWidgets.QFileDialog.getSaveFileName(self, 'Сохранить как', filter='Text files (*.txt)')[0]
        if not directory.endswith('.txt'):
            directory += '.txt'
        if directory and self.tracks and self.string:
            with open(directory, 'w', encoding='utf-8') as d:
                print('{}, {} шт.\n'.format(self.string, len(self.tracks)), file=d)
                for track in self.tracks:
                    print('%(artist)s - %(title)s' % track, file=d)
            self.statusInfo.setText(
                'Список аудиозаписей (без ссылок на скачивание) сохранен в файл {}'.format(directory))

    def download_all(self):
        length = 0
        length += len(self.tracks)
        for album in self.albums:
            length += len(album['tracks'])
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку")
        if directory:
            self.download_audio.statusInfo = self.statusInfo
            self.download_audio.tracks = self.tracks
            self.download_audio.albums = self.albums
            self.download_audio.directory = directory
            self.statusInfo.setText('Процесс скачивания аудиозаписей начался.')
            self.progress_label.setEnabled(True)
            self.progressBar.setEnabled(True)
            self.progressBar.setMaximum(length)
            self.toggle_buttons(False)
            self.download_audio.start()

    def download_selected(self):
        directory = None
        selected = self.trackList.selectedItems()
        selected_tracks = []
        for element in selected:
            for track in self.tracks:
                if element.text(0) in '%(artist)s — %(title)s' % track:
                    selected_tracks.append(track)
                    break
        for element in selected:
            for album in self.albums:
                for track in album['tracks']:
                    if element.text(0) in '%(artist)s — %(title)s' % track:
                        selected_tracks.append(track)
                        break
        if selected_tracks:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку")
        if directory:
            self.download_audio.statusInfo = self.statusInfo
            self.download_audio.tracks = selected_tracks
            self.download_audio.directory = directory
            self.statusInfo.setText('Процесс скачивания аудиозаписей начался.')
            self.progress_label.setEnabled(True)
            self.progressBar.setEnabled(True)
            self.progressBar.setMaximum(len(selected_tracks))
            self.toggle_buttons(False)
            self.download_audio.start()
        else:
            self.statusInfo.setText('<html><head/><body><p><span style=" color:#ff0000;">'
                                    'Ничего не выбрано для скачивания или было отменено диалоговое с выбором папки'
                                    '</span></p></body></html>')

    def done(self, result):
        self.toggle_buttons(True)
        if isinstance(result, str):
            self.statusInfo.setText(result)
        else:
            self.statusInfo.setText('<html><head/><body><p><span style=" color:#ff0000;">При скачивании'
                                    ' произошла ошибка: {}'
                                    '</span></p></body></html>'.format(result))

    def play_track(self):
        self.selected = self.trackList.selectedItems()
        selected_tracks = []
        if self.selected:
            for track in self.tracks:
                if self.selected[0].text(0) in '%(artist)s — %(title)s' % track:
                    selected_tracks.append(track)
                    break
            for album in self.albums:
                for track in album['tracks']:
                    if self.selected[0].text(0) in '%(artist)s — %(title)s' % track:
                        selected_tracks.append(track)
                        break
        else:
            track = choice(self.tracks)
            selected_tracks.append(track)
            self.selected.append(self.trackList.findItems('%(artist)s — %(title)s' % track, Qt.MatchContains)[0])
        local = QUrl(selected_tracks[0]['link'])
        media = QMediaContent(local)
        self.mediaPlayer.setMedia(media)
        self.mediaPlayer.play()
        self.toggle_fields(False)
        self.btnConfirm.setEnabled(False)
        self.trackList.clearSelection()

    def search_tracks(self, query=None):
        for i in self.hidden_tracks:
            i.setHidden(False)
        self.hidden_tracks.clear()
        result = [i.text(0) for i in self.trackList.findItems(query, Qt.MatchContains)]
        for i in range(self.trackList.topLevelItemCount()):
            if self.trackList.topLevelItem(i).text(0) in result:
                pass
            else:
                self.hidden_tracks.append(self.trackList.topLevelItem(i))
                self.trackList.topLevelItem(i).setHidden(True)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Alt:
            if self.mediaPlayer.state():
                self.toggle_fields(True)
                self.toggle_buttons(True)
            self.mediaPlayer.stop()
        elif e.key() == Qt.Key_Up:
            if self.current_volume < 100:
                self.current_volume += 2
                self.mediaPlayer.setVolume(self.current_volume)
            self.statusBar().showMessage('Текущая громкость: {}'.format(self.current_volume))
        elif e.key() == Qt.Key_Down:
            if self.current_volume > 0:
                self.current_volume -= 2
                self.mediaPlayer.setVolume(self.current_volume)
            self.statusBar().showMessage('Текущая громкость: {}'.format(self.current_volume))
        elif e.key() == Qt.Key_Space:
            if self.mediaPlayer.state() == 1:
                self.mediaPlayer.pause()
                self.toggle_fields(False)
                self.toggle_buttons(False)
                self.downloadSelected.setEnabled(True)
            elif self.mediaPlayer.state() == 2:
                self.mediaPlayer.play()
                self.toggle_fields(False)
                self.toggle_buttons(False)
                self.downloadSelected.setEnabled(True)
        elif e.key() == Qt.Key_Left:
            self.mediaPlayer.setPosition(self.mediaPlayer.position() - 2000)
        elif e.key() == Qt.Key_Right:
            self.mediaPlayer.setPosition(self.mediaPlayer.position() + 2000)

    def on_item_expanded(self, item):
        if item.childCount():
            return
        for album in self.albums:
            if album['title'] == item.text(0):
                for track in album['tracks']:
                    QtWidgets.QTreeWidgetItem(item, ['%(artist)s — %(title)s' % track])

    def toggle_buttons(self, state: bool):
        self.downloadAll.setEnabled(state)
        self.saveAll.setEnabled(state)
        self.saveWithoutLinks.setEnabled(state)
        self.downloadSelected.setEnabled(state)
        self.btnConfirm.setEnabled(state)

    def toggle_fields(self, state: bool):
        self.login.setEnabled(state)
        self.password.setEnabled(state)
        self.user_link.setEnabled(state)
        self.trackList.setEnabled(state)
        self.saveData.setEnabled(state)
        self.search.setEnabled(state)