from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import pymysql
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 注册字体
pdfmetrics.registerFont(TTFont('Heiti', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))
pdfmetrics.registerFont(TTFont('Heiti-Bold', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))

def get_db_connection():
    connection = pymysql.connect(host='localhost',
                                 user='hrkq',
                                 password='Qaz1121zz',
                                 database='hrkq',
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        creation_date = request.form['creation_date']
        position = request.form['position']
        disinfectant = request.form['disinfectant']
        type = request.form['type']
        recorder = request.form['recorder']
        notes = request.form['notes']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            sql = '''INSERT INTO disinfection_record (creation_date, position, disinfectant, type, recorder, notes)
                      VALUES (%s, %s, %s, %s, %s, %s)'''
            cursor.execute(sql, (creation_date, position, disinfectant, type, recorder, notes))
            conn.commit()
            flash('录入成功')
        except Exception as e:
            flash(str(e))
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/magic', methods=['POST'])
def magic():
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        success = True
        while current_date <= end_date:
            position = "诊室、大厅"
            disinfectant = "含氯消毒液"
            type = "擦拭、拖地"
            recorder = "李畅" if (current_date - datetime.strptime(start_date, '%Y-%m-%d')).days % 14 < 7 else "成月"
            notes = ""

            sql = '''INSERT INTO disinfection_record (creation_date, position, disinfectant, type, recorder, notes)
                      VALUES (%s, %s, %s, %s, %s, %s)'''
            cursor.execute(sql, (current_date.strftime('%Y-%m-%d'), position, disinfectant, type, recorder, notes))
            current_date += timedelta(days=1)

        conn.commit()
    except Exception as e:
        flash(str(e))
        success = False
    finally:
        cursor.close()
        conn.close()

    return jsonify({'success': success})

@app.route('/print_records')
def print_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''SELECT * FROM disinfection_record
                          WHERE creation_date BETWEEN %s AND %s''', (start_date, end_date))
        records = cursor.fetchall()

        # 创建一个内存中的文件
        from io import BytesIO
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        title_style = ParagraphStyle(name='title_style', fontName='Heiti-Bold', fontSize=22, alignment=1)
        header_style = ParagraphStyle(name='header_style', fontName='Heiti', fontSize=12, alignment=1)
        sign_style = ParagraphStyle(name='sign_style', fontName='Heiti-Bold', fontSize=16, alignment=0)
        
        headers = ['消毒时间', '场所名称', '使用消毒产品', '消毒方式', '经手人', '备注']
        max_rows_per_page = 20  # 设置每页最大行数
        table_data = []  # 初始化表格数据
        current_rows = 0
        add_sign = True  # 用于标记是否需要添加负责人签名文本
        
        # 定义列宽
        colWidths = [1 * inch, 1 * inch, 1.2 * inch, 1 * inch, 0.8 * inch, 2.2 * inch]

        for record in records:
            if current_rows == 0:
                # 在每一页的表格之前添加负责人签名文本
                if add_sign:
                    elements.append(Paragraph('负责人签名：', sign_style))
                    elements.append(Spacer(1, 24))  # 添加一些间距
                    add_sign = False
                # 确保每页开始时都添加表头
                table_data = [headers]  # 在每页的开始添加表头

            if current_rows >= max_rows_per_page:
                # 当前行数达到每页最大行数，创建表格并添加到文档
                table = Table(table_data, colWidths=colWidths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Heiti'),
                    ('FONTSIZE', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, 'black'),  # 添加外边框
                    ('GRID', (1, 1), (-2, -2), 1, 'black'),  # 添加内边框
                    ('WIDTH', (-1, 0), (-1, -1), 5 * inch),  # 设置最后一列的宽度
                ]))
                elements.append(table)
                elements.append(PageBreak())  # 添加分页
                elements.append(Paragraph('负责人签名：', sign_style))
                elements.append(Spacer(1, 24))  # 添加一些间距
                table_data = [headers]  # 重置表格数据
                current_rows = 0

            table_data.append([
                record['creation_date'].strftime('%Y-%m-%d'),
                record['position'],
                record['disinfectant'],
                record['type'],
                record['recorder'],
                record['notes']
            ])
            current_rows += 1

        # 添加最后一个表格到文档
        if table_data:
            table = Table(table_data, colWidths=colWidths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Heiti'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, 'black'),  # 添加外边框
                ('GRID', (1, 1), (-2, -2), 1, 'black'),  # 添加内边框
                ('WIDTH', (-1, 0), (-1, -1), 5 * inch),  # 设置最后一列的宽度
            ]))
            elements.append(table)

        doc.build(elements)

        # 将内存中的文件转换为响应
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="records.pdf")
    except Exception as e:
        flash(str(e))
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)