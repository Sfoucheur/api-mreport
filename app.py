# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
from flask_restplus import Api, Resource, fields
from sqlalchemy import create_engine, bindparam, Integer, String, event, func,desc
#from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql import text
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.schema import CreateSchema, DropSchema
from functions_inc import *
from collections import defaultdict

class CherrokeeFix(object):

    def __init__(self, app, script_name, scheme):
        self.app = app
        self.script_name = script_name
        self.scheme = scheme

    def __call__(self, environ, start_response):
        path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
        environ['wsgi.url_scheme'] = self.scheme
        environ['SCRIPT_NAME'] = self.script_name
        environ['PATH_INFO'] = path[len(self.script_name):]
        return self.app(environ, start_response)



app = Flask(__name__)
app.config.from_object('config')
app.config['JSON_AS_ASCII'] = False
db = SQLAlchemy(app)
try :
    schema = app.config['SCHEMA']
    event.listen(db.metadata, 'before_create', CreateSchema(schema))
    event.listen(db.metadata, 'after_drop', DropSchema(schema))

    #  Uncomment these lines to insert sample data when creating the database  
    #  event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/alimentation.sql",schema+".")))
except KeyError :
    # Uncomment these lines to insert sample data when creating the database
    '''
    event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/dataid.sql","")))
    event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/report.sql","")))
    event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/dataviz.sql","")))
    event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/report_composition.sql","")))
    event.listen(db.metadata, "after_create", db.DDL(insertdb("Datainit/rawdata.sql","")))
    '''
    print("If you want to add a schema edit config.py with SCHEMA variable")
    
from models import *

app.wsgi_app = CherrokeeFix(app.wsgi_app, app.config['APP_PREFIX'], app.config['APP_SCHEME'])
api = Api(app=app, version='0.1', title='MReport Api', description='Test API', validate=True) #,doc=False

store = api.namespace('store', description='Store de dataviz')
report = api.namespace('report', description='Reports')
report_composition = api.namespace('report_composition', description='Composition des rapports')
report_html = api.namespace('report_html', description='Structure html des rapports')

@store.route('/',doc={'description':'Récupération des dataviz'})
class GetCatalog(Resource):
    def get(self):
        result = db.session.query(Dataviz).all()
        data = {'datavizs': json.loads(json.dumps([row2dict(r) for r in result]))}
        return jsonify(**data)

dataviz_put = store.model('Dataviz_put', {
    'title': fields.String(max_length=200,required=True),
    'description': fields.String(max_length=250,required=False),
    'source': fields.String(max_length=200,required=True),
    'year': fields.String(max_length=4,required=False),
    'unit': fields.String(max_length=50,required=False),
    'type': fields.String(max_length=200,required=True),
    'level': fields.String(max_length=50,required=True),
    'job': fields.String(max_length=50,required=False)
})
dataviz_post = api.model('Dataviz_post', {
    'title': fields.String("the title",max_length=200),
    'description': fields.String(max_length=250),
    'source': fields.String(max_length=200),
    'year': fields.String(max_length=4),
    'unit': fields.String(max_length=50),
    'type': fields.String(max_length=200),
    'level': fields.String(max_length=50),
    'job': fields.String(max_length=50)
})

@store.route('/<string:dataviz_id>/data/sample',doc={'Données':'Données associées à une dataviz'})
class DatavizData(Resource):
    def get(self, dataviz_id):
        result = db.session.query(Rawdata.dataset, Rawdata.order,Rawdata.label,Rawdata.data).filter(Rawdata.dataviz == dataviz_id).filter(Rawdata.dataid.in_(db.session.query(db.func.max(Rawdata.dataid)).filter(Rawdata.dataviz == dataviz_id).all())).order_by(Rawdata.dataset,Rawdata.order).all()
        '''
            db.session.query(Rawdata.dataset, Rawdata.order,Rawdata.label,Rawdata.data)
            .filter(Rawdata.dataviz == dataviz_id)
            .filter(Rawdata.dataid.in_(db.session.query(db.func.max(Rawdata.dataid)).filter(Rawdata.dataviz == dataviz_id).all()))
            .order_by(Rawdata.dataset,Rawdata.order).all()
        '''
        data = {'items': json.loads(json.dumps(dict_builder(result)))}
        return jsonify(**data)

@store.route('/<string:dataviz_id>',doc={'description':'Création/Modification/Suppression d\'une dataviz'})
class DatavizManagement(Resource):
    @store.expect(dataviz_put)
    def put(self, dataviz_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if Dataviz.query.get(dataviz_id):
                return {"response": "dataviz already exists."}, 403
            else:
                print("Avant "+str(data))
                data.update({'dataviz':dataviz_id})
                print("Après "+str(data))
                try:
                    dvz = Dataviz(**data)
                except TypeError as err:
                    return {"response": str(err)}, 400
                #**data will unpack the dict object, so if have data = {'dataviz': 'test', 'name': 'Awesome'}, Dataviz(**data) will do like Dataviz(dataviz='test', name='Awesome')
                db.session.add(dvz)
                db.session.commit()
                return {"response": "success" , "data": data}
    @store.expect(dataviz_post)
    def post(self, dataviz_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if Dataviz.query.get(dataviz_id):
                dvz = Dataviz.query.get(dataviz_id)
                for fld in ["title", "description", "source", "year", "type", "level", "unit", "job"]:
                    value = data.get(fld)
                    if value:
                        setattr(dvz, fld, value)

                db.session.commit()
                return {"response": "success" , "data": data, "dataviz":dataviz_id}
            else:
                return {"response": "dataviz doesn't exists."}, 404


    def delete(self, dataviz_id):
        dvz = Dataviz.query.get(dataviz_id)
        if dvz:
            db.session.delete(dvz)
            db.session.commit()
            return {"response": "success", "dataviz":dataviz_id}
        else:
            return {"response": "The dataviz does not exists."}, 404


@report.route('/', doc={'description': 'Récupération des rapports avec leurs dataviz associées'})
class GetReports(Resource):
    def get(self):
        result = db.session.query(Report,Report_composition.dataviz).outerjoin(Report_composition,Report.report == Report_composition.report).all()
        '''
                db.session.query(Report,Report_composition.dataviz)
                .outerjoin(Report_composition,Report.report == Report_composition.report)
                .all()
        '''
        data = dict_builder(result)
        res = defaultdict(list)
        for values in data: res[values['report'],values['title']].append(values['dataviz'])
        data = {'reports': [{'report':report[0],'title':report[1], 'dataviz':dataviz} for report,dataviz in res.items()]}
        return jsonify(**data)

report_fields = api.model('Report', {
    'title': fields.String(max_length=250,required=True)
})
@report.route('/<report_id>', doc={'description':'Récupération/Création/Modification/Suppression d\'un rapport'})
@report.doc(params={'report_id': 'identifiant du rapport'})
class GetReport(Resource):
    def get(self,report_id):
        result = db.session.query(Rawdata.dataid.label("dataid"),Dataid.label.label("label")).distinct().join(Report_composition,Rawdata.dataviz == Report_composition.dataviz).join(Dataid,Dataid.dataid == Rawdata.dataid).filter(Report_composition.report == report_id).order_by(desc(Dataid.label)).all()
        '''
                db.session.query(Rawdata.dataid.label("dataid"),Dataid.label.label("label"))
                .distinct()
                .join(Report_composition,Rawdata.dataviz == Report_composition.dataviz)
                .join(Dataid,Dataid.dataid == Rawdata.dataid)
                .filter(Report_composition.report == id)
                .order_by(desc(Dataid.label))
                .all()
        '''
        data = {'items': json.loads(json.dumps(dict_builder(result)))}
        return jsonify(**data)
    @report.expect(report_fields)
    def put(self,report_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if Report.query.get(report_id):
                return {"response": "The report already exists."}, 403
            else:
                data.update({"report":report_id})
                try:
                    rep = Report(**data)
                except TypeError as err:
                    return {"response": str(err)}, 400
                source = "/".join([app.config['MREPORT_LOCATION'], "reports", "models", "default"])
                destination = "/".join([app.config['MREPORT_LOCATION'], "reports", report_id])
                fss = createFileSystemStructure(source, destination)
                if fss == 'success':
                    db.session.add(rep)
                    db.session.commit()
                    return {"response": "success" , "data": data, "report":report_id}
                else:
                    return {"response": "Error" , "error": fss}
    @report.expect(report_fields)
    def post(self, report_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if Report.query.get(report_id):
                rep = Report.query.get(report_id)
                for fld in ["title"]:
                    value = data.get(fld)
                    if value:
                        setattr(rep, fld, value)
                db.session.commit()
                return {"response": "success" , "data": data, "report":report_id}
            else:
                return {"response": "report doesn't exists."}, 404
    def delete(self, report_id):
        rep = Report.query.get(report_id)
        folder = "/".join([app.config['MREPORT_LOCATION'], "reports", report_id])
        if rep:
            delete_folder = deleteFileSystemStructure(folder)
            if delete_folder == 'success':
                db.session.delete(rep)
                db.session.commit()
                return {"response": "success", "report":report_id}
            else:
                return {"response": delete_folder}
        else:
            return {"response": "The report '"+report_id+"' does not exists."}, 404

@report.route('/<report_id>/<dataid_id>', doc={'description': 'Récupération des données pour rapport ex: test & 200039022'})
@report.doc(params={'report_id': 'identifiant du rapport', 'dataid_id': 'id géographique'})
class GetReport(Resource):
    def get(self, report_id, dataid_id):
        result = db.session.query(Rawdata).join(Report_composition,Rawdata.dataviz == Report_composition.dataviz).filter(Report_composition.report == report_id).filter(Rawdata.dataid == dataid_id).all()
        '''
                db.session.query(Rawdata)
                .join(Report_composition,Rawdata.dataviz == Report_composition.dataviz)
                .filter(Report_composition.report == id)
                .filter(Rawdata.dataid == idgeo)
                .all()
        '''
        data = {'data': json.loads(json.dumps([row2dict(r) for r in result]))}
        return jsonify(**data)
report_composition_fields = api.model('Report_composition', {
    'dataviz': fields.String(max_length=50,required=True)
})
@report_composition.route('/<report_id>', doc={'description': 'Composition et Supression d\'un rapport'})
@report_composition.doc(params={'report_id': 'identifiant du rapport'})
class GetReportComposition(Resource):
    @report.expect([report_composition_fields])
    def put(self,report_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if not Report.query.get(report_id):
                return {"response": "report does not exists."}, 404
            else:
                dtv_list = []
                for dvz in data :
                    if not Dataviz.query.get(dvz["dataviz"]):
                        data = {"response": "ERROR dataviz \'"+dvz["dataviz"]+"\' does not exist"}
                        return data, 404
                    if Report_composition.query.filter_by(report=report_id,dataviz=dvz["dataviz"]).first():
                        data = {"response": "ERROR the report is already associated with \'"+dvz["dataviz"]+"\'"}
                        return data, 406
                    dvz.update({"report":report_id})
                    try:
                        rep_comp = Report_composition(**dvz)
                    except TypeError as err:
                        return {"response": str(err)}, 400
                    dtv_list.append(rep_comp)
                for rep_c in dtv_list :
                    db.session.add(rep_c)
                    db.session.commit()
                return {"response": "success" , "data": data}
    @report.expect([report_composition_fields])
    def delete(self,report_id):
        data = request.get_json()
        if not data:
            data = {"response": "ERROR no data supplied"}
            return data, 405
        else:
            if not Report.query.get(report_id):
                return {"response": "report does not exists."}, 404
            else:
                dtv_list = []
                for dvz in data :

                    if not Dataviz.query.get(dvz["dataviz"]):
                        data = {"response": "ERROR dataviz \'"+dvz["dataviz"]+"\' does not exist"}
                        return data, 404
                    rep_comp = Report_composition.query.filter_by(report=report_id,dataviz=dvz["dataviz"]).first()
                    if not rep_comp:
                        data = {"response": "ERROR the report is not associated with \'"+dvz["dataviz"]+"\'"}
                        return data, 405
                    dtv_list.append(rep_comp)
                for rep_c in dtv_list :
                    db.session.delete(rep_c)
                    db.session.commit()
                return {"response": "success" , "data": data, "report":report_id}

    @report_html.route('/<report_id>', doc={'description': 'Structure HTML d\'un rapport'})
    @report_html.doc(params={'report_id': 'identifiant du rapport'})
    class updateReportStructure(Resource):
        def post(self,report_id):
            html = request.get_data(as_text=True)
            if not html:
                data = {"response": "ERROR no data supplied"}
                return data, 405
            else:
                up = updateReportHTML("/".join([app.config['MREPORT_LOCATION'], "reports", report_id, "report.html"]), html)
                return {"response": up}




if __name__ == "__main__":
    app.run(host='127.0.0.1')
