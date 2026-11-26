"""Экспорт журнала ошибок и расшифровок в Excel."""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side
from openpyxl.worksheet.hyperlink import Hyperlink

import DISC_INFO
import FAULT_WORDS
from RS_handler import FaultsBuffer, RsWorker
from fault_buffer_table import FAULT_BUFFER_HEADERS, fault_buffer_row


DETAIL_HEADERS = ('Buffer', 'Address', 'Field', 'HEX', 'BIT', 'NAME', 'SETTING')
LINE = Side(style='thin', color='000000')


def _setup_sheet(sheet, headers, widths, freeze):
    sheet.append(headers)
    sheet.freeze_panes = freeze
    sheet.row_dimensions[1].height = 28
    for column, width in enumerate(widths, start=1):
        cell = sheet.cell(1, column)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        sheet.column_dimensions[cell.column_letter].width = width


def _append_detail(sheet, buffer_index, address, field, raw_hex, fields):
    first_row = sheet.max_row + 1
    for bit, name, setting in fields:
        sheet.append((None, None, None, None, bit, name, setting))
    last_row = sheet.max_row

    for column, value in enumerate((buffer_index, address, field, raw_hex), start=1):
        sheet.merge_cells(start_row=first_row, start_column=column,
                          end_row=last_row, end_column=column)
        cell = sheet.cell(first_row, column, value)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for row in range(first_row, last_row + 1):
        for column in range(1, 8):
            sheet.cell(row, column).border = Border(
                left=LINE, right=LINE,
                top=LINE if row == first_row else Side(),
                bottom=LINE if row == last_row else Side(),
            )
    return first_row


def _link_to_detail(cell, sheet_name, row):
    cell.hyperlink = Hyperlink(
        ref=cell.coordinate,
        location=f"'{sheet_name}'!A{row}",
        tooltip='Open decoded table',
    )


def build_nvm_workbook(raw_buffs):
    book = Workbook()
    summary = book.active
    summary.title = 'Fault buffers'
    disc1_sheet = book.create_sheet('DISC_INFO1')
    disc2_sheet = book.create_sheet('DISC_INFO2')
    words_sheet = book.create_sheet('Fault words')
    raw_sheet = book.create_sheet('NVM raw')

    summary_widths = [min(38, max(12, len(header) + 2)) for header in FAULT_BUFFER_HEADERS]
    _setup_sheet(summary, FAULT_BUFFER_HEADERS, summary_widths, 'C2')
    for sheet in (disc1_sheet, disc2_sheet, words_sheet):
        _setup_sheet(sheet, DETAIL_HEADERS, (10, 12, 26, 12, 10, 46, 30), 'C2')
    _setup_sheet(raw_sheet, ('Address', 'Byte', 'Buffer', 'Offset'),
                 (14, 10, 10, 10), 'A2')

    header_columns = {name: column for column, name in enumerate(FAULT_BUFFER_HEADERS, start=1)}
    buffer_count = len(raw_buffs) // FaultsBuffer.SIZE
    for index, offset in enumerate(range(0, len(raw_buffs), FaultsBuffer.SIZE)):
        buffer = FaultsBuffer(raw_buffs[offset:offset + FaultsBuffer.SIZE])
        values = fault_buffer_row(index, buffer)
        address = values[header_columns['Address'] - 1]
        summary.append(values)
        for cell in summary[summary.max_row]:
            cell.alignment = Alignment(horizontal='center', vertical='center')

        for number, sheet in ((1, disc1_sheet), (2, disc2_sheet)):
            field = f'DISC_INFO{number}'
            value = getattr(buffer, field.lower())
            first_row = _append_detail(
                sheet, index, address, field, f'{value:06X}H',
                DISC_INFO.decode_disc_info(number, value),
            )
            _link_to_detail(summary.cell(summary.max_row, header_columns[field]),
                            sheet.title, first_row)

        for field in FAULT_WORDS.WORD_START_CODES:
            value = getattr(buffer, field.lower())
            first_row = _append_detail(
                words_sheet, index, address, field, f'{value:04X}H',
                FAULT_WORDS.decode_fault_word(field, value),
            )
            _link_to_detail(summary.cell(summary.max_row, header_columns[field]),
                            words_sheet.title, first_row)

        if index + 1 < buffer_count:
            for sheet in (disc1_sheet, disc2_sheet, words_sheet):
                empty_row = sheet.max_row + 1
                sheet.row_dimensions[empty_row].height = 15
                sheet.cell(empty_row, 1)

    for sheet in (summary, disc1_sheet, disc2_sheet, words_sheet):
        sheet.auto_filter.ref = f'A1:{sheet.cell(1, sheet.max_column).column_letter}{sheet.max_row}'

    for index, value in enumerate(raw_buffs):
        address = RsWorker.FAULT_MEMORY_START + index * 2
        raw_sheet.append((
            f'{address:04X}H', value,
            index // RsWorker.FAULT_BUFFER_SIZE,
            index % RsWorker.FAULT_BUFFER_SIZE,
        ))
    raw_sheet.auto_filter.ref = f'A1:D{raw_sheet.max_row}'
    return book
