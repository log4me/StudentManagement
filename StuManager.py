#!/usr/bin/env python
# encoding: utf-8


from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
from werkzeug.utils import secure_filename
import sqlite3
import os
import sys
import xlrd
reload(sys)
sys.setdefaultencoding('utf-8')
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'score')
ALLOWED_EXTENSIONS = set(['xls','XLS'],)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.update(dict(
    DATABASE=os.path.join(app.root_path,'School.db'),
    DEBUG=False,
    SECRET_KEY='NiCaiBuDao',
))

#	---------------数据库连接start---------------
def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if not hasattr(g,'sqlite_db'):  # 未连接数据库
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g,'sqlite_db'):
        g.sqlite_db.close()
#	--------------数据库连接end------------------------

#	--------------用户管理部分start----------------------
@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

@app.route('/login',methods=['POST','GET'])
def login():
    error = None
    cursor = get_db()
    if request.method == "POST" :
        sql = "select * from user where username = ?"
        result_set = cursor.execute(sql,(request.form['username'],))
        result = result_set.fetchone()
        if not result :
            error = "用户名不存在"
        elif result[1] != request.form['password'] :
            error = "密码错误"
        elif result[2] != request.form['role'] :
            error = "角色错误"
        else: 
            error = None
            session['role'] = request.form['role']
            session['username'] = request.form['username']
            session['lasttime'] = result[3]
            session['period'] = cursor.execute("select period from period").fetchone()[0]
            cursor.execute("update user set lasttime = datetime('now','localtime') where username=?",(request.form['username'],))
            cursor.commit()
            msg = "登陆成功,欢迎"+result[0]+"上次登录时间为："+result[3]
            return redirect(url_for(session['role']+'_frame'))
    return render_template('login.html',error=error)
@app.route('/logoutall')
def logoutall():
    return render_template('logoutall.html')

@app.route('/logout')
def logout(info = None):
    error = None
    session.pop('role', None)
    session.pop('username', None)
    session.pop('lasttime', None)
    return redirect(url_for('login'))

@app.route('/change_password',methods=['POST','GET'])
def change_password():
    if not session.get('role'):
        error = "您尚未登录"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        oldpassword = request.form['oldpassword']
        newpassword = request.form['newpassword']
        confirmpassword = request.form['confirmpassword']
        if newpassword != confirmpassword :
            return fail_msg("确认密码不匹配，请重新输入",return_url=url_for('change_password'))
        username = session['username']
        cursor =get_db()
        confirmpass = cursor.execute("select * from user where username = ? and password = ? ",(username,oldpassword)).fetchone()
        if confirmpass :
            cursor.execute("update user set password = ? where username = ?",(newpassword,username))
            cursor.commit()
            return success_msg(content="密码修改成功,请重新登录",return_url="/logoutall")
        else :
            return fail_msg(content = "旧密码不正确，请重新输入",return_url="/change_password")

    return render_template('change_password.html')
#   ---------------用户部分end---------------------

#   ---------------管理员页面start-----------------
@app.route('/admin_main')
def admin_main():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    cursor = get_db()
    count_s = cursor.execute("select count(*) from student").fetchone()[0]
    count_t = cursor.execute("select count(*) from teacher").fetchone()[0]
    count_c = cursor.execute("select count(*) from course").fetchone()[0]
    period = cursor.execute("select period from period").fetchone()[0]
    data = dict()
    data['username'] = session['username']
    data['lasttime'] = session['lasttime']
    data['count_c'] = count_c
    data['count_s'] = count_s
    data['count_t'] = count_t
    data['period'] = period
    return render_template('admin_main.html',data=data)

@app.route('/admin_frame')
def admin_frame():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_frame.html')

@app.route('/admin_cou')
def admin_cou():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_cou.html')

@app.route('/admin_cou_add',methods=['POST','GET'])
def admin_cou_add():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cursor = get_db()
        cno = request.form['cno']
        cname = request.form['cname']
        ccredit = request.form['ccredit']
        result_set=cursor.execute("select * from course where cno =?",(cno,))
        if result_set.fetchone():
            return fail_msg(content="该课程已存在",return_url='/admin_cou_add')
        else:
            sql="insert into course(cno,cname,ccredit) values(?,?,?)"
            cursor.execute(sql, (cno,cname,ccredit))
            cursor.commit()
            return success_msg(content="成功添加课程",return_url=url_for('admin_cou_add'))
    return render_template('admin_cou_add.html')

@app.route('/admin_cou_import',methods=['POST','GET'])
def admin_cou_import():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        import_xls = request.files['import_xls']
        if import_xls and allowed_file(import_xls.filename) :
            import_xls_name = secure_filename(import_xls.filename)
            import_xls.save(os.path.join(app.config['UPLOAD_FOLDER'], import_xls_name))
        stu_table = xlrd.open_workbook('static/score/'+import_xls_name).sheets()[0]
        count_row = stu_table.nrows
        cursor = get_db()
        for i in range(count_row) :
            cno = stu_table.row_values(i)[0]
            cname = stu_table.row_values(i)[1]
            ccredit = int(stu_table.row_values(i)[2])
            result_set=cursor.execute("select * from course where cno =?",(cno,))
            if not result_set.fetchone():
                sql="insert into course(cno,cname,ccredit) values(?,?,?)"
                cursor.execute(sql, (cno,cname,ccredit))
                cursor.commit()
        cursor.commit()
        return success_msg(content="成功导入课程",return_url=url_for('admin_cou_add'))
    return render_template('admin_cou_add.html')

@app.route('/admin_cou_del',methods=['POST','GET'])
@app.route('/admin_cou_del/<cno>',methods=['POST','GET'])
def admin_cou_del(cno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not cno:
        return render_template('admin_cou_del.html')
    cursor = get_db()
    if not cno :
        cno = request.form['cno']
    result_set=cursor.execute("select * from course where cno =?",(cno,))
    if not result_set.fetchone():
        return fail_msg(content="该课程不存在",return_url='/admin_cou_del')
    cou = cursor.execute("select * from tc where cno =?",(cno,)).fetchone()
    if cou :
        return fail_msg("有教师开设此课程，不可删除",'/admin_cou_del')
    cursor.execute("delete from course where cno=?", (cno,))
    cursor.commit()
    return success_msg(content="删除成功",return_url=url_for('admin_cou_del'))
 
    
@app.route('/admin_cou_sel')
def admin_cou_sel():
    if not session.get('role') or (session['role'] != 'admin' and session['role'] != 'teacher') :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_cou_sel.html')

@app.route('/admin_cou_selrs',methods=['POST','GET'])
def admin_cou_selrs():
    if not session.get('role') or (session['role'] != 'admin' and session['role'] != 'teacher') :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cno = '%'+request.form['cno']+'%'
        cname = '%'+request.form['cname']+'%'
        ccredit = '%'+request.form['ccredit']+'%'
        sql = "select * from course where cno like ? and cname like ? and ccredit like ?"
        cursor = get_db()
        result_set = cursor.execute(sql, (cno, cname, ccredit)) 
        cous = result_set.fetchall()
        data = []
        for cou in cous :
            info = dict()
            info['cno'] = cou[0]
            info['cname'] = cou[1]
            info['ccredit'] = cou[2]
            data.append(info)
        return render_template('admin_cou_selrs.html', data=data)
    return render_template('admin_cou_sel.html')

@app.route('/admin_cou_set')
@app.route('/admin_cou_set/<period>')
def admin_cou_set(period=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if period == 'begin' :
        cursor = get_db()
        sql = "update period set period='选课'"
        cursor.execute(sql)
        sql = "update period set date=datetime('now','localtime')"
        cursor.commit()
        session['period'] = "选课"
        return success_msg(content=u"开始选课设定成功", return_url='/admin_cou_set')
    elif period == 'end' :
        cursor = get_db()
        sql = "update period set period='学习'"
        cursor.execute(sql)
        sql = "update period set date=datetime('now','localtime')"
        cursor.commit()
        session['period'] = "学习"
        return success_msg(content=u'结束选课设定成功', return_url='/admin_cou_set')
    else :
        return render_template('admin_cou_set.html')

@app.route('/admin_cou_upd',methods=['POST','GET'])
@app.route('/admin_cou_upd/<cno>',methods=['POST','GET'])
def admin_cou_upd(cno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not cno :
        return render_template('admin_cou_upd.html')
    if not cno :
        cno = request.form['cno']
    cursor = get_db()
    result_set = cursor.execute("select * from course where cno=?",(cno,))
    data = result_set.fetchone()
    if data :
        return render_template('admin_cou_updrs.html',data=data)
    else :
        return fail_msg(content="该课程不存在",return_url="/admin_cou_upd")


@app.route('/admin_cou_updrs',methods=['POST','GET'])
def admin_cou_updrs():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cursor = get_db()
        cno = request.form['cno']
        cname = request.form['cname']
        ccredit = request.form['ccredit']
        cursor.execute("update course set cname=?,ccredit=? where cno = ?",(cname, ccredit, cno))
        cursor.commit()
        return success_msg(content="课程信息更新成功", return_url='/admin_cou_upd')
    return render_template('admin_cou_upd.html')

@app.route('/admin_navi')
def admin_navi():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_navi.html')

@app.route('/admin_stu')
def admin_stu():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_stu.html')

#增加学生
@app.route('/admin_stu_add',methods=['POST','GET'])
def admin_stu_add():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cursor = get_db()
        sno = request.form['sno']
        sname = request.form['sname']
        ssex = request.form['ssex']
        sage = request.form['sage']
        sdept = request.form['sdept']
        sphone = request.form['sphone']
        spassword = request.form['spassword']
        result_set=cursor.execute("select * from student where sno =?",(sno,))
        if result_set.fetchone():
            return fail_msg(content="该学生已存在",return_url='/admin_stu_add')
        else:
            sql="insert into student(sno,sname,ssex,sage,sdept,sphone) values(?,?,?,?,?,?)"
            cursor.execute(sql, (sno,sname,ssex,sage,sdept,sphone))
            cursor.execute("insert into user(username,password,role,lasttime) values(?,?,?,?)", (sno,spassword,'student',u'您是第一次登陆系统'))
            cursor.commit()
            return success_msg(content="成功添加该学生",return_url=url_for('admin_stu_add'))
    return render_template('admin_stu_add.html')

@app.route('/admin_stu_import',methods=['POST','GET'])
def admin_stu_import():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        import_xls = request.files['import_xls']
        if import_xls and allowed_file(import_xls.filename) :
            import_xls_name = secure_filename(import_xls.filename)
            import_xls.save(os.path.join(app.config['UPLOAD_FOLDER'], import_xls_name))
        stu_table = xlrd.open_workbook('static/score/'+import_xls_name).sheets()[0]
        count_row = stu_table.nrows
        cursor = get_db()
        for i in range(count_row) :
            sno = stu_table.row_values(i)[0]
            sname = stu_table.row_values(i)[1]
            ssex = stu_table.row_values(i)[2]
            sage = int(stu_table.row_values(i)[3])
            sdept = stu_table.row_values(i)[4]
            sphone = int(stu_table.row_values(i)[5])
            spassword = stu_table.row_values(i)[6]
            result_set=cursor.execute("select * from student where sno =?",(sno,))
            if not result_set.fetchone():
                sql="insert into student(sno,sname,ssex,sage,sdept,sphone) values(?,?,?,?,?,?)"
                cursor.execute(sql, (sno,sname,ssex,sage,sdept,sphone))
                cursor.execute("insert into user(username,password,role,lasttime) values(?,?,?,?)", (sno,spassword,'student',u'您是第一次登陆系统'))
        cursor.commit()
        return success_msg(content="成功导入学生",return_url=url_for('admin_stu_add'))
    return render_template('admin_stu_add.html')
#删除学生
@app.route('/admin_stu_del/<sno>',methods=['POST','GET'])
@app.route('/admin_stu_del',methods=['POST','GET'])
def admin_stu_del(sno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not sno:
        return render_template('admin_stu_del.html')
    cursor = get_db()
    if not sno:
        sno = request.form['sno']
    result_set=cursor.execute("select * from student where sno =?",(sno,))
    if not result_set.fetchone():
        return fail_msg(content="该学生不存在",return_url='/admin_stu_del')
    cursor.execute("delete from user where username=?", (sno,))
    cursor.execute("delete from student where sno=?", (sno,))
    cursor.execute("delete from sc where sno=?",(sno,))
    cursor.commit()
    return success_msg(content="删除成功",return_url=url_for('admin_stu_del'))


@app.route('/admin_stu_sel')
def admin_stu_sel():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_stu_sel.html')

@app.route('/admin_stu_selrs',methods=['POST','GET'])
def admin_stu_selrs():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        sno = '%'+request.form['sno']+'%'
        sname = '%'+request.form['sname']+'%'
        sdept = '%'+request.form['sdept']+'%'
        sql = "select * from student where sno like ? and sname like ? and sdept like ?"
        cursor = get_db()
        result_set = cursor.execute(sql, (sno, sname, sdept)) 
        stus = result_set.fetchall()
        data = []
        for stu in stus :
            info = dict()
            password = cursor.execute("select password from user where username= ?", (stu[0],)).fetchone()[0]
            sum_credit = cursor.execute("select sum(ccredit) from sc ,course\
                                         where sc.cno = course.cno and grade >60 and sno =?", (stu[0],)).fetchone()
            avg_grade = cursor.execute("select avg(grade) from sc,course\
                                         where sc.cno=course.cno and sno=?",(stu[0],)).fetchone()
            info['sno'] = stu[0]
            info['sname'] = stu[1]
            info['ssex'] = stu[2]
            info['sage'] = stu[3]
            info['sphone'] = stu[4]
            info['sdept'] = stu[5]
            info['spassword'] = password;
            if  not avg_grade  or not avg_grade[0]:
                info['avg_grade'] = 0
            else :
                info['avg_grade'] = avg_grade[0]
            rank = cursor.execute("select count(*)+1 as count\
                                  from (select sno ,avg(grade) as stu_avg\
                                  from sc,course where sc.cno=course.cno group by sno)\
                                  where stu_avg>?",(info['avg_grade'],)).fetchone()
            if rank :
                info['rank'] = rank[0]
            else :
                info['rank'] = 1
            if  sum_credit and sum_credit[0]:
                info['sum_credit'] = sum_credit[0]
            else :
                info['sum_credit'] = 0
            data.append(info)
        return render_template('admin_stu_selrs.html', data=data)
    return redirect(url_for('admin_stu_sel'))
# 更新学生信息
@app.route('/admin_stu_upd',methods=['GET','POST'])
@app.route('/admin_stu_upd/<sno>',methods=['GET','POST'])
def admin_stu_upd(sno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not sno:
        return render_template('admin_stu_upd.html')
    if not sno :
        sno = request.form['sno']
    cursor = get_db()
    result_set = cursor.execute("select * from student where sno=?",(sno,))
    data = result_set.fetchone()
    if data :
        password = cursor.execute("select password from user where username = ?",(sno,)).fetchone()[0]
        return render_template('admin_stu_updrs.html',data=data,spassword=password)
    else :
        return fail_msg(content="该学生不存在",return_url="/admin_stu_upd")

@app.route('/admin_stu_updrs',methods=['GET','POST'])
def admin_stu_updrs():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
        return success_msg(content="学生信息更新成功", return_url='/admin_stu_upd')
    if request.method == 'POST' :
        cursor = get_db()
        sno = request.form['sno']
        sname = request.form['sname']
        ssex = request.form['ssex']
        sage = request.form['sage']
        sdept = request.form['sdept']
        sphone = request.form['sphone']
        spassword = request.form['spassword']
        cursor.execute("update student set sname=?,sage=?,ssex=?,sdept=?,sphone=? where sno=?",(sname,sage,ssex,sdept,sphone,sno))
        cursor.execute("update user set password=? where username = ?",(spassword,sno))
        cursor.commit()
        return success_msg(content="学生信息更新成功", return_url='/admin_stu_upd')
    return render_template('admin_stu_upd.html')

@app.route('/admin_tea')
def admin_tea():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_tea.html')

@app.route('/admin_tea_add',methods=['POST','GET'])
def admin_tea_add():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST':
        tno = request.form['tno']
        tname = request.form['tname']
        tphone = request.form['tphone']
        tpassword = request.form['tpassword']
        cursor = get_db()
        result_set = cursor.execute("select * from teacher where tno=?",(tno,))
        if result_set.fetchone():
            return fail_msg(content='教师工号已存在', return_url='/admin_tea_add')
        cursor.execute("insert into teacher(tno,tname,tphone) values(?,?,?)",(tno,tname,tphone))
        cursor.execute("insert into user(username,password,role,lasttime) values(?,?,?,?)",(tno,tpassword,'teacher',u'您是第一次登陆系统'))
        cursor.commit()
        return success_msg(content='教师录入成功', return_url='/admin_tea_add')
    return render_template('admin_tea_add.html')
@app.route('/admin_tea_import',methods=['POST','GET'])
def admin_tea_import():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        import_xls = request.files['import_xls']
        if import_xls and allowed_file(import_xls.filename) :
            import_xls_name = secure_filename(import_xls.filename)
            import_xls.save(os.path.join(app.config['UPLOAD_FOLDER'], import_xls_name))
        stu_table = xlrd.open_workbook('static/score/'+import_xls_name).sheets()[0]
        count_row = stu_table.nrows
        cursor = get_db()
        for i in range(count_row) :
            tno = stu_table.row_values(i)[0]
            tname = stu_table.row_values(i)[1]
            tphone = int(stu_table.row_values(i)[2])
            tpassword = stu_table.row_values(i)[3]
            result_set=cursor.execute("select * from teacher where tno =?",(tno,))
            if not result_set.fetchone():
                sql="insert into teacher(tno,tname,tphone) values(?,?,?)"
                cursor.execute(sql, (tno,tname,tphone))
                cursor.execute("insert into user(username,password,role,lasttime) values(?,?,?,?)", (tno,tpassword,'teacher',u'您是第一次登陆系统'))
        cursor.commit()
        return success_msg(content="成功导入教师",return_url=url_for('admin_tea_add'))
    return render_template('admin_tea_add.html')

#删除教师
@app.route('/admin_tea_del/<tno>',methods=['POST','GET'])
@app.route('/admin_tea_del',methods=['POST','GET'])
def admin_tea_del(tno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not tno:
        return render_template('admin_tea_del.html')
    cursor = get_db()
    if not tno:
        tno = request.form['tno']
    result_set = cursor.execute("select * from teacher where tno=?",(tno,))
    if not result_set.fetchone():
            return fail_msg(content='教师工号不存在', return_url='/admin_tea_del')
    cou = cursor.execute("select * from tc where tno=?",(tno,)).fetchone()
    if cou :
        return fail_msg("此教师开始的有课程，不可删除",'/admin_tea_del')
    cursor.execute("delete from user where username=?", (tno,))
    cursor.execute("delete from teacher where tno=?", (tno,))
    cursor.commit()
    return success_msg(content="删除成功",return_url=url_for('admin_tea_del'))

@app.route('/admin_tea_sel')
def admin_tea_sel():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    return render_template('admin_tea_sel.html')

@app.route('/admin_tea_selrs',methods=['POST','GET'])
def admin_tea_selrs():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        tno = '%'+request.form['tno']+'%'
        tname = '%'+request.form['tname']+'%'
        sql = "select * from teacher where tno like ? and tname like ?"
        cursor = get_db()
        result_set = cursor.execute(sql, (tno, tname)) 
        teas = result_set.fetchall()
        data = []
        for tea in teas :
            info = dict()
            tpassword = cursor.execute("select password from user where username= ?", (tea[0],)).fetchone()[0]
            info['tno'] = tea[0]
            info['tname'] = tea[1]
            info['tphone'] = tea[2]
            info['tpassword'] = tpassword
            data.append(info)
        return render_template('admin_tea_selrs.html', data=data)
    return render_template('admin_tea_selrs.html')

@app.route('/admin_tea_upd',methods=['POST','GET'])
@app.route('/admin_tea_upd/<tno>',methods=['POST','GET'])
def admin_tea_upd(tno=None):
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method != 'POST' and not tno :
        return render_template('admin_tea_upd.html')
    cursor = get_db()
    if not tno :
        tno = request.form['tno']
    result_set = cursor.execute("select * from teacher where tno=?",(tno,))
    data = result_set.fetchone()
    if data :
        password = cursor.execute("select password from user where username = ?",(tno,)).fetchone()[0]
        return render_template('admin_tea_updrs.html',data=data,tpassword=password)
    else :
        return fail_msg(content="该教师不存在",return_url="/admin_tea_upd")
    return render_template('admin_tea_upd.html')


@app.route('/admin_tea_updrs',methods=['POST','GET'])
def admin_tea_updrs():
    if not session.get('role') or session['role'] != 'admin' :
        error = "您尚未登录或您不是管理员"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cursor = get_db()
        tno = request.form['tno']
        tname = request.form['tname']
        tphone = request.form['tphone']
        tpassword = request.form['tpassword']
        cursor.execute("update teacher set tname=?,tphone=? where tno=?",(tname,tphone,tno))
        cursor.execute("update user set password=? where username = ?",(tpassword,tno))
        cursor.commit()
        return success_msg(content="教师信息更新成功", return_url='/admin_tea_upd')
    return render_template('admin_tea_upd.html')

#   --------------------管理员end---------------

#   --------------------student start---------------

@app.route('/student_cho')
def student_cho():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_cho.html')

@app.route('/student_cho_del/<cno>',methods=['POST','GET'])
def student_cho_del(cno):
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    cursor = get_db()
    if cursor.execute("select period from period ").fetchone()[0] != "选课":
        return fail_msg("现在不是选课时期，不能删除课程")
    cursor.execute("delete from sc where sno=? and cno=?",(session['username'],cno))  
    print session['username']
    cursor.commit()
    return success_msg("删除成功","/student_cho_sub")
@app.route('/student_cho_sel',methods=['POST','GET'])
def student_cho_sel():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cno = '%'+request.form['cno']+'%'
        cname = '%'+request.form['cname']+'%'
        ccredit = '%'+request.form['ccredit']+'%'
        ctime = '%'+request.form['ctime1'] + request.form['ctime2']+'%'
        clocation = '%'+request.form['clocation']+'%'
        tname = '%'+request.form['tname']+'%'
        cursor = get_db()
        result_set = cursor.execute("select course.cno,cname,ccredit,clocation,cmaxcount,teacher.tno,tname,ctime from teacher,tc,course where\
                                    tc.cno=course.cno and tc.tno=teacher.tno and tc.tno like ? and cname like ? and ccredit like ? and ctime like ?\
                                    and clocation like ? and tname like ?",(cno,cname,ccredit,ctime,clocation,tname)).fetchall()
        data = []
        for cou in result_set :
            info =dict()
            info['cno'] = cou[0]
            info['cname'] = cou[1]
            info['ccredit'] = cou[2]
            info['clocation'] = cou[3]
            info['cmaxcount'] = cou[4]
            info['tno'] = cou[5]
            info['tname'] = cou[6]
            info['ctime'] = cou[7]
            res = cursor.execute("select count(*) from sc where cno=?",(cou[0],)).fetchone()
            info['cselected'] = res[0]
            data.append(info)
        return render_template('student_cho_selrs.html',data=data)
    return render_template('student_cho_sel.html')
@app.route('/student_cho_sel_cno/<cno>',methods=['POST','GET'])
def student_cho_sel_cno(cno=None):
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    if not cno :
        return fail_msg("该课程不存在！")
    cursor = get_db()
    cou = cursor.execute("select course.cno,cname,ccredit,clocation,cmaxcount,teacher.tno,tname,ctime from teacher,tc,course where\
                                    tc.cno=course.cno and tc.tno=teacher.tno and tc.cno=?",(cno,)).fetchone()
    data = []
    info =dict()
    info['cno'] = cou[0]
    info['cname'] = cou[1]
    info['ccredit'] = cou[2]
    info['clocation'] = cou[3]
    info['cmaxcount'] = cou[4]
    info['tno'] = cou[5]
    info['tname'] = cou[6]
    info['ctime'] = cou[7]
    res = cursor.execute("select count(*) from sc where cno=?",(cou[0],)).fetchone()
    info['cselected'] = res[0]
    data.append(info)
    return render_template('student_cho_selrs.html',data=data)
@app.route('/student_cou_cloud')
def student_cou_cloud():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    cous = cursor.execute("select sc.cno,cname,count(*) as count from sc,course where sc.cno = course.cno group by sc.cno order by sc.cno desc limit 0,10").fetchall()
    tags = "<tags>"
    for cou in cous :
        link = "<a href='/student_cho_sel_cno/"+cou[0]+"' style='22' color='0xff0000' hicolor='0x00cc00'>"+cou[0]+"</a>"
        tags = tags + link
    tags = tags + "</tags>"
    print "zheli"
    print tags
    return render_template('tags_cloud.html',title='热门课程',tags=tags)

#学生标签云
@app.route('/student_stu_sel_sno/<sno>',methods=['POST','GET'])
def student_sel_sno(sno=None):
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    stu = cursor.execute("select * from student where sno=?", (sno,)).fetchone()
    data = []
    info = dict()
    sum_credit = cursor.execute("select sum(ccredit) from sc ,course\
                                 where sc.cno = course.cno and grade >60 and sno =?", (stu[0],)).fetchone()
    avg_grade = cursor.execute("select avg(grade) from sc,course\
                                 where sc.cno=course.cno and sno=?",(stu[0],)).fetchone()
    info['sno'] = stu[0]
    info['sname'] = stu[1]
    info['ssex'] = stu[2]
    info['sage'] = stu[3]
    info['sphone'] = stu[4]
    info['sdept'] = stu[5]
    if  not avg_grade  or not avg_grade[0]:
        info['avg_grade'] = 0
    else :
        info['avg_grade'] = avg_grade[0]
    rank = cursor.execute("select count(*)+1 as count\
                          from (select sno ,avg(grade) as stu_avg\
                          from sc,course where sc.cno=course.cno group by sno)\
                          where stu_avg>?",(info['avg_grade'],)).fetchone()
    if rank :
        info['rank'] = rank[0]
    else :
        info['rank'] = 1
    if  sum_credit and sum_credit[0]:
        info['sum_credit'] = sum_credit[0]
    else :
        info['sum_credit'] = 0
    data.append(info)
    return render_template('student_sel_other_rs.html',data=data)

@app.route('/student_stu_cloud')
def student_stu_cloud():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    stus = cursor.execute("select sc.sno,sname,avg(grade) as avg from sc,student where sc.sno= student.sno group by sc.sno order by avg desc limit 0,10").fetchall()
    tags = "<tags>"
    for stu in stus :
        link = "<a href='/student_stu_sel_sno/"+stu[0]+"' style='22' color='0xff0000' hicolor='0x00cc00'>"+stu[0]+"</a>"
        tags = tags + link
    tags = tags + "</tags>"
    return render_template('tags_cloud.html',title='学生排名',tags=tags)
@app.route('/student_cho_selrs')
def student_cho_selrs():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_cho_sel.html')

@app.route('/student_cho_sub',methods=['POST','GET'])
def student_cho_sub():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    cursor = get_db()
    if request.method == 'POST' :
        if cursor.execute("select period from period").fetchone()[0] != "选课" :
            return fail_msg("现在不是选课时期，不能选择课程",'/student_cho_sub')
        cno = request.form['cno']
        exist = cursor.execute("select * from tc where cno=?",(cno,)).fetchone()
        if not exist or not exist[0] :
            return fail_msg(content="该课程不存在!", return_url="/student_cho_sub")
        ctime = cursor.execute("select ctime from tc where cno=?",(cno,)).fetchone()[0]
        time_conflict =  cursor.execute("select * from sc,tc where sc.cno=tc.cno and sno=? and ctime=?",(session['username'],ctime)).fetchone()
        if time_conflict :
            return fail_msg("您的上课时间与此课程冲突，请调节后进行选择",'/student_cho_sub')
        cmaxcount = cursor.execute("select cmaxcount from tc where cno=?",(cno,)).fetchone()[0]
        cselected = cursor.execute("select count(*) from sc where cno=?",(cno,)).fetchone()[0]
        if cmaxcount <= cselected :
            return fail_msg("该课程容量已满，请选择其他课程",return_url="/student_cho_sub")
        cursor.execute("insert into sc(sno,cno) values(?,?)",(session['username'],cno))
        cursor.commit()
        return success_msg("选课成功!",return_url="/student_cho_sub")
    cous = cursor.execute("select sc.cno,cname,ccredit,tname,ctime,clocation from course,sc,tc,teacher where sc.sno=? and course.cno=sc.cno and tc.cno=sc.cno and tc.tno=teacher.tno",(session['username'],)).fetchall()
    return render_template('student_cho_sub.html',cous=cous)
@app.route('/student_cho_sub_cno/<cno>',methods=['POST','GET'])
def student_cho_sub_cno(cno):
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    cursor = get_db()
    if cursor.execute("select period from period").fetchone()[0] != "选课" :
        return fail_msg("现在不是选课时期，不能选择课程",'/student_cho_sub')
    exist = cursor.execute("select * from tc where cno=?",(cno,)).fetchone()
    if not exist or not exist[0] :
        return fail_msg(content="该课程不存在!", return_url="/student_cho_sub")
    ctime = cursor.execute("select ctime from tc where cno=?",(cno,)).fetchone()[0]
    time_conflict =  cursor.execute("select * from sc,tc where sc.cno=tc.cno and sno=? and ctime=?",(session['username'],ctime)).fetchone()
    if time_conflict :
        return fail_msg("您的上课时间与此课程冲突，请调节后进行选择",'/student_cho_sub')
    cmaxcount = cursor.execute("select cmaxcount from tc where cno=?",(cno,)).fetchone()[0]
    cselected = cursor.execute("select count(*) from sc where cno=?",(cno,)).fetchone()[0]
    if cmaxcount <= cselected :
        return fail_msg("该课程容量已满，请选择其他课程",return_url="/student_cho_sub")
    cursor.execute("insert into sc(sno,cno) values(?,?)",(session['username'],cno))
    cursor.commit()
    return success_msg("选课成功!",return_url="/student_cho_sub")
@app.route('/student_frame')
def student_frame():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_frame.html')

@app.route('/student_main')
def student_main():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    cursor = get_db()
    info = dict()
    stu = cursor.execute("select sno,sname,ssex,sdept from student where sno=?",(session['username'],)).fetchone()
    sum_credit = cursor.execute("select sum(ccredit) from sc ,course\
                                 where sc.cno = course.cno and grade >60 and sno =?", (stu[0],)).fetchone()
    avg_grade = cursor.execute("select avg(grade) from sc,course\
                                where sc.cno=course.cno and sno=?",(stu[0],)).fetchone()
    info['sno'] = stu[0]
    info['sname'] = stu[1]
    info['sdept'] = stu[2]
    info['lasttime'] = session['lasttime']
    info['period'] = cursor.execute("select period from period").fetchone()[0]
    if info['period'] == '选课' :
        info['message'] = "你可以进行选课"
    else :
        info['message'] = "你可以查看已选课程"
    if  not avg_grade  or not avg_grade[0]:
        info['avg_grade'] = 0
    else :
        info['avg_grade'] = avg_grade[0]
    rank = cursor.execute("select count(*)+1 as count\
                          from (select sno ,avg(grade) as stu_avg\
                          from sc,course where sc.cno=course.cno group by sno)\
                          where stu_avg>?",(info['avg_grade'],)).fetchone()
    if rank :
        info['rank'] = rank[0]
    else :
        info['rank'] = 1
    if  sum_credit and sum_credit[0]:
        info['sum_credit'] = sum_credit[0]
    else :
        info['sum_credit'] = 0
    return render_template('student_main.html',stu_info=info)


@app.route('/student_menu')
def student_menu():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_menu.html')

@app.route('/student_navi')
def student_navi():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_navi.html')

@app.route('/student_sel')
def student_sel():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    return render_template('student_sel.html')

@app.route('/student_sel_other')
def student_sel_other():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    return render_template('student_sel_other.html')

@app.route('/student_sel_other_cours/<sno>',methods=['POST','GET'])
def student_sel_other_cours(sno):
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    cous = cursor.execute("select sc.cno,cname,ccredit,ctime,clocation,grade,cstatus from course,sc,tc where sc.sno=? and course.cno=sc.cno and tc.cno=sc.cno",(sno,)).fetchall()
    data = dict() 
    for cou in cous :
        if cou[6] == "已提交" :
            info = dict() 
            info['rank'] = cursor.execute("select count(*)+1 from sc where cno=? and grade>?",(cou[0],cou[5])).fetchone()[0]
            data[cou[0]] = info
    return render_template('student_sel_other_cours.html',data=data,cous=cous,sno=sno)

@app.route('/student_sel_other_rs',methods=['POST','GET'])
def student_sel_other_rs():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        sno = '%'+request.form['sno']+'%'
        sdept = '%'+request.form['sdept']+'%'
        sname = '%'+request.form['sname']+'%'
        cursor = get_db()
        result_set = cursor.execute("select * from student where sno like ? and sname like ? and sdept like ?", (sno, sname, sdept)) 
        stus = result_set.fetchall()
        data = []
        for stu in stus :
            info = dict()
            sum_credit = cursor.execute("select sum(ccredit) from sc ,course\
                                         where sc.cno = course.cno and grade >60 and sno =?", (stu[0],)).fetchone()
            avg_grade = cursor.execute("select avg(grade) from sc,course\
                                         where sc.cno=course.cno and sno=?",(stu[0],)).fetchone()
            info['sno'] = stu[0]
            info['sname'] = stu[1]
            info['ssex'] = stu[2]
            info['sage'] = stu[3]
            info['sphone'] = stu[4]
            info['sdept'] = stu[5]
            if  not avg_grade  or not avg_grade[0]:
                info['avg_grade'] = 0
            else :
                info['avg_grade'] = avg_grade[0]
            rank = cursor.execute("select count(*)+1 as count\
                                  from (select sno ,avg(grade) as stu_avg\
                                  from sc,course where sc.cno=course.cno group by sno)\
                                  where stu_avg>?",(info['avg_grade'],)).fetchone()
            if rank :
                info['rank'] = rank[0]
            else :
                info['rank'] = 1
            if  sum_credit and sum_credit[0]:
                info['sum_credit'] = sum_credit[0]
            else :
                info['sum_credit'] = 0
            data.append(info)
        return render_template('student_sel_other_rs.html',data=data)
    return render_template('student_sel_other.html')

@app.route('/student_sel_self')
def student_sel_self():
    if not session.get('role') or session['role'] != 'student' :
        error = "您尚未登录或您不是学生"
        return render_template("login.html",error=error)
    cursor = get_db()
    cous = cursor.execute("select sc.cno,cname,ccredit,ctime,clocation,grade,cstatus from course,sc,tc where sc.sno=? and course.cno=sc.cno and tc.cno=sc.cno",(session['username'],)).fetchall()
    data = dict() 
    for cou in cous :
        if cou[6] == "已提交" :
            info = dict() 
            info['rank'] = cursor.execute("select count(*)+1 from sc where cno=? and grade>?",(cou[0],cou[5])).fetchone()[0]
            data[cou[0]] = info
    return render_template('student_sel_self.html',cous=cous,data=data)

#   --------------student end----------------------

#   --------------teacher start--------------------
@app.route('/teacher_cho')
def teacher_cho():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    data =dict()
    data['tno'] = session['username']
    return render_template('teacher_cho.html',data=data)

@app.route('/teacher_cho_del',methods=['POST','GET'])
def teacher_cho_del():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    cursor =get_db() 
    period = cursor.execute("select period from period").fetchone()[0]
    if period != '选课' :
        return fail_msg(content="现在不是选课时期，不能删除课程")
    tno = session['username']
    if request.method == 'POST' :
        cnos = request.form.getlist('to_delete')
        for cno in cnos :
            print "here"
            print cno
            cursor.execute("delete from tc where cno =?",(cno,))
        cursor.commit()
        return success_msg(content="删除成功", return_url="/teacher_cho_del") 
    else :
        cous = cursor.execute("select * from tc where tno = ?",(tno,)).fetchall()
        data = []
        if cous :
            for cou in cous :
                info = dict()
                info['cno'] = cou[1]
                res = cursor.execute("select cname,ccredit from course where cno = ?",(cou[1],)).fetchone()
                info['cname'] = res[0]
                info['ccredit'] = res[1]
                result = cursor.execute("select count(*) from sc where cno = ?",(info['cno'],)).fetchone()
                if result : 
                    info['cstudentcount'] = result[0]
                else :
                    info['cstudentcount'] = 0
                if info['cstudentcount'] == 0 :
                    data.append(info)
        return render_template('teacher_cho_del.html',data=data)

@app.route('/teacher_cho_sel')
def teacher_cho_sel():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_cho_sel.html')

@app.route('/teacher_cho_selrs',methods=['POST','GET'])
def teacher_cho_selrs():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        cno = '%'+request.form['cno']+'%'
        cname = '%'+request.form['cname']+'%'
        ccredit = '%'+request.form['ccredit']+'%'
        sql = "select * from course where cno like ? and cname like ? and ccredit like ?"
        cursor = get_db()
        result_set = cursor.execute(sql, (cno, cname, ccredit)) 
        cous = result_set.fetchall()
        data = []
        for cou in cous :
            info = dict()
            info['cno'] = cou[0]
            info['cname'] = cou[1]
            info['ccredit'] = cou[2]
            data.append(info)
        return render_template('teacher_cho_selrs.html', data=data)
    return render_template('teacher_cho_sel.html')

@app.route('/teacher_cho_sel_cno/<cno>',methods=['POST','GET'])
def teacher_cho_sel_cno(cno=None):
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    sql = "select * from course where cno=?"
    cursor = get_db()
    result_set = cursor.execute(sql, (cno,)) 
    cou = result_set.fetchone()
    data = []
    info = dict()
    info['cno'] = cou[0]
    info['cname'] = cou[1]
    info['ccredit'] = cou[2]
    data.append(info)
    return render_template('teacher_cho_selrs.html', data=data)
@app.route('/teacher_cho_set',methods=['POST','GET'])
def teacher_cho_set():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    data = dict()
    cursor = get_db()
    period = cursor.execute("select period from period").fetchone()[0]
    data['period'] = period
    if period != '选课' :
        return fail_msg(content="现在不是选课时期，不能开设课程")
    if request.method == 'POST' :
        cno = request.form['cno'].rsplit('-',2)[0]
        tno = session['username'] 
        clocation = request.form['clocation']
        try :
            cmaxcount = int(request.form['cmaxcount'])
        except(ValueError) :
            return fail_msg("课程容量应该是数字！","/teacher_cho_set")
        ctime = request.form['ctime1'] + request.form['ctime2']
        result_set = cursor.execute("select * from tc where tno=? and ctime=?",(tno,ctime)).fetchone()
        if result_set :
            return fail_msg('您在当前时间内已有开设课程，请选择其他时间', 'teacher_cho_set')
        result_set=cursor.execute("select * from course where cno =?",(cno,))
        if result_set.fetchone():
            result_set = cursor.execute("select * from tc where cno = ?",(cno,))
            if result_set.fetchone() :
                return fail_msg(content="该课程已有教师开设，请选择其他课程", return_url="/teacher_cho_set")
            sql="insert into tc(tno,cno,clocation,cmaxcount,ctime) values(?,?,?,?,?)"
            cursor.execute(sql, (tno,cno,clocation,cmaxcount,ctime))
            cursor.commit()
            return success_msg(content="成功开设课程",return_url=url_for('teacher_cho_set'))
        else:
            return fail_msg(content="该课程不存在，请让管理员添加课程后再开设课程",return_url='/teacher_cho_set')
    cous = cursor.execute("select * from course")
    return render_template('teacher_cho_set.html',data=data,cous=cous)

@app.route('/teacher_cho_seted/<tno>')
def teacher_cho_seted(tno):
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    cous = cursor.execute("select * from tc where tno = ?",(tno,)).fetchall()
    data = []
    if cous :
        for cou in cous :
            info = dict()
            info['cno'] = cou[1]
            res = cursor.execute("select cname,ccredit from course where cno = ?",(cou[1],)).fetchone()
            info['cname'] = res[0]
            info['ccredit'] = res[1]
            info['clocation'] = cou[2]
            info['ctime'] = cou[4]
            info['cmaxcount'] = cou[3]
            result = cursor.execute("select count(*) from sc where cno = ?",(info['cno'],)).fetchone()
            if result : 
                info['cstudentcount'] = result[0]
            else :
                info['cstudentcount'] = 0
            data.append(info)
        return render_template('teacher_cho_seted.html',data=data,tno=tno)
    else :
        return render_template('teacher_cho_seted.html',data=None,tno=tno)
@app.route('/teacher_frame')
def teacher_frame():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_frame.html')

@app.route('/teacher_main')
def teacher_main():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    cursor = get_db()
    tname = cursor.execute("select tname from teacher where tno =?",(session['username'],))
    period = cursor.execute("select period from period").fetchone()[0]
    data = dict()
    data['tno'] = session['username']
    data['tname'] = tname.fetchone()[0]
    data['lasttime'] = session['lasttime']
    data['period'] = period
    if period == '选课' :
        data['message'] = u"你可以开设课程或信息查询,或提交成绩"
    else :
        data['message'] = u"你可以进行信息查询或提交成绩。"
    return render_template('teacher_main.html',data=data)

@app.route('/teacher_menu')
def teacher_menu():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_menu.html')

@app.route('/teacher_navi')
def teacher_navi():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_navi.html')

@app.route('/teacher_cou_cloud')
def teacher_cou_cloud():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    cous = cursor.execute("select sc.cno,cname,count(*) as count from sc,course where sc.cno = course.cno group by sc.cno order by sc.cno desc limit 0,10").fetchall()
    tags = "<tags>"
    for cou in cous :
        link = "<a href='/teacher_cho_sel_cno/"+cou[0]+"' style='22' color='0xff0000' hicolor='0x00cc00'>"+cou[0]+"</a>"
        tags = tags + link
    tags = tags + "</tags>"
    return render_template('tags_cloud.html',title='热门课程',tags=tags)

@app.route('/teacher_tea_cloud')
def teacher_tea_cloud():
    if not session.get('role') :
        error = "您尚未登录"
        return render_template("login.html",error=error)
    cursor = get_db()
    teas = cursor.execute("select tc.tno,tname,count(*) as count from sc,tc,teacher where sc.cno=tc.cno and tc.tno=teacher.tno group by tc.tno order by count desc limit 0,10").fetchall()
    tags = "<tags>"
    for tea in teas :
        link = "<a href='/teacher_sel_other_tno/"+tea[0]+"' style='22' color='0xff0000' hicolor='0x00cc00'>"+tea[0]+"</a>"
        tags = tags + link
    tags = tags + "</tags>"
    return render_template('tags_cloud.html',title='热门教师',tags=tags)
@app.route('/teacher_sel_other_tno/<tno>')
def teacher_sel_other_tno(tno=None):
    if not session.get('role'):
        error = "您尚未登录"
        return render_template("login.html",error=error)
    sql = "select * from teacher where tno=?"
    cursor = get_db()
    result_set = cursor.execute(sql, (tno,)) 
    tea = result_set.fetchone()
    data = []
    info = dict()
    info['tno'] = tea[0]
    info['tname'] = tea[1]
    info['tphone'] = tea[2]
    data.append(info)
    return render_template('teacher_sel_other_rs.html', data=data)
@app.route('/teacher_sel')
def teacher_sel():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_sel.html')

@app.route('/teacher_sel_other')
def teacher_sel_other():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_sel_other.html')

@app.route('/teacher_sel_other_rs',methods=['POST','GET'])
def teacher_sel_other_rs():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    if request.method == 'POST' :
        tno = '%'+request.form['tno']+'%'
        tname = '%'+request.form['tname']+'%'
        sql = "select * from teacher where tno like ? and tname like ?"
        cursor = get_db()
        result_set = cursor.execute(sql, (tno, tname)) 
        teas = result_set.fetchall()
        data = []
        for tea in teas :
            info = dict()
            info['tno'] = tea[0]
            info['tname'] = tea[1]
            info['tphone'] = tea[2]
            data.append(info)
        return render_template('teacher_sel_other_rs.html', data=data)
    return render_template('teacher_sel_other.html')

@app.route('/teacher_sel_self')
def teacher_sel_self():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    sql = "select * from teacher where tno = ?"
    cursor = get_db()
    result_set = cursor.execute(sql, (session['username'],))
    tea = result_set.fetchone()
    tdata = dict() 
    tdata['tno'] = tea[0]
    tdata['tname'] = tea[1]
    tdata['tphone'] = tea[2]
    tdata['tpassword'] = cursor.execute("select password from user where username= ?", (tea[0],)).fetchone()[0]
    cdata = []
    cous = cursor.execute("select course.cno,course.cname,course.ccredit from tc,course where tc.cno=course.cno and tno=? group by course.cno,course.cname,course.ccredit",(tdata['tno'],)).fetchall()
    score = dict()
    for cou in cous :
        info = dict()
        res = cursor.execute("select avg(grade),max(grade),min(grade),count(*) from sc where cno = ?",(cou[0],)).fetchone()
        if res :
            if  res[0]:
                info["avg_grade"] = res[0]
            else :
                info["avg_grade"] = 0
            if res[1] :
                info["max_grade"] = res[1]
            else :
                info["max_grade"] = 0
            if res[2] :
                info["min_grade"] = res[2]
            else :
                info["min_grade"] = 0
            if res[3] :
                info["count"] = res[3]
            else :
                info["count"] = 0
        else :
            info["avg_grade"] = 0
            info["max_grade"] = 0
            info["min_grade"] = 0
            info["count"] = 0
        score[cou[0]] = info
    return render_template('teacher_sel_self.html', tdata=tdata,cous=cous,score=score)

@app.route('/teacher_sel_self_coul/<cno>')
def teacher_sel_self_coul(cno):
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    cursor = get_db()
    ccredit = cursor.execute("select ccredit from course where cno=?",(cno,)).fetchone()[0]
    snos = cursor.execute("select sno from sc where cno=?",(cno,)).fetchall()
    data = dict()
    data['cstatus'] = cursor.execute("select cstatus from tc where cno=?",(cno,)).fetchone()[0]
    for sno in snos :
        info =dict()
        info['sname'] = cursor.execute("select sname from student where sno=?",(sno[0],)).fetchone()[0]
        info["rank"] = cursor.execute("select count(*)+1 as count from sc as a,sc as b where a.grade>b.grade and a.cno=b.cno and a.cno=? and b.sno=?",(cno,sno[0])).fetchone()[0]
        info["grade"] = cursor.execute("select grade from sc where sno=? and cno=?",(sno[0],cno)).fetchone()[0]
        if not info["grade"] :
            info["grade"] = 0
        data[sno[0]] = info
    return render_template('teacher_sel_self_coul.html',ccredit=ccredit,cno=cno,snos=snos,data=data)

@app.route('/teacher_sub')
def teacher_sub():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_sub.html')

@app.route('/teacher_sub_cl/<status>',methods=['POST','GET'])
def teacher_sub_cl(status):
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    cursor = get_db()
    if status == 'subed' :
        result_set = cursor.execute("select tc.cno,cname from tc,course where tc.cno=course.cno and tc.cstatus=? and tno=?",(u"已提交",session['username'])).fetchall()
    else :
        result_set = cursor.execute("select tc.cno,cname from tc,course where tc.cno=course.cno and (tc.cstatus is null or tc.cstatus!=?) and tno=?",(u"已提交",session['username'])).fetchall()
    return render_template('teacher_sub_cl.html',data=result_set,cstatus=status)

@app.route('/teacher_sub_input')
def teacher_sub_input():
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    return render_template('teacher_sub_input.html')

@app.route('/teacher_sub_score/<cno>',methods=['POST','GET'])
def teacher_sub_score(cno) :
    if not session.get('role') or session['role'] != 'teacher' :
        error = "您尚未登录或您不是教师"
        return render_template("login.html",error=error)
    score_xls = request.files[cno]
    if score_xls and allowed_file(score_xls.filename) :
        score_xls_name = secure_filename(score_xls.filename)
        score_xls.save(os.path.join(app.config['UPLOAD_FOLDER'], score_xls_name))
    score_table = xlrd.open_workbook('static/score/'+score_xls_name).sheets()[0]
    count_row = score_table.nrows
    cursor = get_db()
    str1 = "" 
    for i in range(count_row) :
        sno = score_table.row_values(i)[0]
        grade = score_table.row_values(i)[1]
        exist = cursor.execute("select * from sc where sno=?",(sno,)).fetchone()
        if exist :
            cursor.execute("update sc set grade=? where cno=? and sno=?",(grade,cno,sno))
    cursor.execute("update tc set cstatus=? where cno=?",(u"已提交",cno))
    cursor.commit()
    return success_msg("成绩上传成功",'/teacher_sub_cl/subing')


#   --------------teacher end--------------------

#   --------------util start--------------------------
def success_msg(content,return_url = None):
    if not return_url :
        return '<img src='+url_for('static', filename='image/t.png')+' ><font size=6 color=red>'+content+'</font>'
    else :
        return '<meta http-equiv="refresh" content=1;url="'+return_url+'">' +'\n'+'<img src='+url_for('static', filename='image/t.png')+' ><font size=6 color=red>'+content+'</font>'

def fail_msg(content,return_url = None):
    if not return_url :
        return '<img src='+url_for('static',filename='image/f.png')+'><font size=6 color=red>'+content+'</font>'
    else :
        return '<meta http-equiv="refresh" content=1;url="'+return_url+'">' +'\n'+'<img src='+url_for('static',filename='image/f.png')+'><font size=6 color=red>'+content+'</font>'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
#   --------------util end--------------------------
#	---------------run----------------------------
if __name__ == '__main__' :
	app.run(port=8080)
