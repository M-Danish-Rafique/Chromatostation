from datetime import datetime


def create_professional_audit_pdf(save_path, company, start_dt, end_dt, data):
    """Create a professional audit trail PDF with proper formatting"""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfgen import canvas as pdfcanvas

    # Custom page template with header/footer
    class NumberedCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdfcanvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_number(num_pages)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def draw_page_number(self, page_count):
            self.setFont("Helvetica", 9)
            page_num = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(letter[0] - 0.55*inch, 0.5*inch, page_num)

    # Create document
    doc = SimpleDocTemplate(
        save_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        spaceBefore=0,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    # Build content
    elements = []

    # Title
    title = Paragraph("Audit Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.05*inch))

    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#333333'),
                               spaceAfter=0.1*inch, spaceBefore=0.05*inch))

    elements.append(Spacer(1, 0.1*inch))

    meta_data = [
        ["Company Name:", company],
        ["Audit Period Start:", start_dt.strftime('%d/%m/%Y %I:%M:%S %p PKT')],
        ["Audit Period End:", end_dt.strftime('%d/%m/%Y %I:%M:%S %p PKT')],
        ["Report Generated:", datetime.now().strftime('%d/%m/%Y %I:%M:%S %p PKT')],
        ["Total Records:", str(len(data))]
    ]

    meta_table = Table(meta_data, colWidths=[2*inch, 4.5*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.2*inch))

    # Data table header
    elements.append(Paragraph("Audit Records", heading_style))
    elements.append(Spacer(1, 0.1*inch))

    # Sort records by Date Acquired (ascending)
    def _parse_date_acquired(entry):
        date_str = entry.get('date_acquired', '').replace(' PKT', '').strip()
        # Enforce dd/mm/yyyy date format to avoid ambiguity
        for fmt in ('%d/%m/%Y %I:%M:%S %p', '%d/%m/%Y %H:%M:%S'):
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        # Return max for invalid/unsupported formats so they are sorted last
        return datetime.max

    data = sorted(data, key=_parse_date_acquired)

    table_data = [[
        'Sample Name',
        'Injection',
        'Proc Ch Descr.',
        'Date Acquired',
        'Date Processed'
    ]]

    for entry in data:
        table_data.append([
            entry.get('sample_name', ''),
            entry.get('injection', ''),
            entry.get('processed_channel_descr', ''),
            entry.get('date_acquired', ''),
            entry.get('date_processed', '')
        ])

    page_width = letter[0] - 1.0*inch

    injection_width = 0.7*inch
    proc_ch_width = 1.0*inch
    date_acq_width = 1.75*inch
    date_proc_width = 1.75*inch

    fixed_total = injection_width + proc_ch_width + date_acq_width + date_proc_width
    sample_name_width = page_width - fixed_total - 0.1*inch

    col_widths = [sample_name_width, injection_width, proc_ch_width, date_acq_width, date_proc_width]

    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    data_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#444444')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1.0, colors.black),
        ('LINEBELOW', (0, 1), (-1, -2), 0.25, colors.black),
    ]))

    elements.append(data_table)

    doc.build(elements, canvasmaker=NumberedCanvas)
