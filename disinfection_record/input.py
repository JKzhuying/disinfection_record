from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import pymysql
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 注册字体
pdfmetrics.registerFont(TTFont('Heiti', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))

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
        # 获取表单数据
        creation_date = request.form['creation_date']
        position = request.form['position']
        disinfectant = request.form['disinfectant']
        type = request.form['type']
        recorder = request.form['recorder']
        notes = request.form['notes']

        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 插入数据
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
            type = "擦拭"
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

# 确保 PDF 文件的目录存在
pdf_dir = '/home/hrkq/文档/HRKQ/disinfection_record'
if not os.path.exists(pdf_dir):
    os.makedirs(pdf_dir)

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

        # 指定 PDF 文件的路径
        filepath = os.path.join(pdf_dir, "records.pdf")

        # 生成 PDF 文件
        response = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter  # Get the size of the page

        # 设置字体为黑体
        response.setFont("Heiti", 16)
        response.drawString(30, height - 40, "消毒记录")
        response.line(30, height - 50, 30 + 500, height - 50)  # A horizontal line

        y = height - 80
        for record in records:
            text = f"日期: {record['creation_date']}, 位置: {record['position']}, 消毒剂: {record['disinfectant']}, 类型: {record['type']}, 记录人: {record['recorder']}, 备注: {record['notes']}"
            response.drawString(30, y, text)
            y -= 20

        response.save()

        # Send the PDF file to the client
        return send_file(filepath, as_attachment=True, download_name="records.pdf")
    except Exception as e:
        flash(str(e))
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)