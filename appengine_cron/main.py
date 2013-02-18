#!/usr/bin/env python  
# import logging
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
import urllib
import logging
from xml.etree import ElementTree as etree



class BcnTrafficCron(webapp.RequestHandler):
    def get(self):
      
      #grab the data from the BCN open data site
      urlStr = "http://www.bcn.cat/transit/dades/dadestrams.dat"
      result = urlfetch.fetch(urlStr)
      if result.status_code != 200:
        mail.send_mail(sender="jatorre@gmail.com",
            to="jatorre@cartodb.com",
            subject="Problem updating data ON SOURCE on service bcn_traffic! HTTP CODE: %s" %(result.status_code),
            body="URL:%s\n\n\n %s" %(urlStr,result.content))
        #cancel
        logging.info("SOURCE failed: %s" %(urlStr))
        return
      
      
      #raw data from service
      raw_data = result.content    
      
      # prepare the SQL to insert in CartoDB
      # here goes a trick. I want to only insert the data in case it is new, i mean, it is data that i have not loaded
      # already. We can do all in one single statement that will insert if the data is new or not/
      # thats why this SQL looks more complicated.
      rows = raw_data.split("\n")
      sql = "INSERT INTO bcn_traffic_stats(tram_id,status_date,status,status_in_15min) SELECT * FROM ( VALUES "
      for row in rows:
        tram = row.split("#")
        if len(tram)==4:
          sql += "(%s,to_timestamp('%s','YYYYMMDDHH24MISS'),%s,%s),"%(tram[0],tram[1],tram[2],tram[3])
          status_date=tram[1]
      sql=sql[:-1]
      
      sql+=") as n(tram_id,status_date,status,status_in_15min) "
      sql+="WHERE (SELECT max(status_date) FROM bcn_traffic_stats) < to_timestamp('%s','YYYYMMDDHH24MISS')"%(status_date)
      
      form_fields = {
        'api_key' :'XXXXXX',
        'q'       :sql
      }
      form_data = urllib.urlencode(form_fields)
              
      result = urlfetch.fetch(url="https://osm2.cartodb.com/api/v1/sql",
                              payload=form_data,
                              method=urlfetch.POST,
                              headers={'Content-Type': 'application/x-www-form-urlencoded'})
      #If the call fails send an email to notify that there is a problem with the service
      if result.status_code != 200:
        mail.send_mail(sender="jatorre@gmail.com",
            to="jatorre@cartodb.com",
            subject="Problem updating data ON CARTODB on service bcn_traffic: "+str(result.content),
            body="URL:"+urlStr +"\n\n\n"+ result.content)



class MadTrafficCron(webapp.RequestHandler):
    ns='{http://earth.google.com/kml/2.2}'
    data_url = "http://informo.munimadrid.es/informo/tmadrid/tramos.kml"
    def get(self):
      raw_data = self.download_traffic_info()
      xml = etree.fromstring(raw_data)
      document = xml.find("%sDocument" % (self.ns))
      self.delete_old_traffic()
      self.create_new_traffic(document.findall('%sPlacemark' % (self.ns)))
      
    def download_traffic_info(self):
      result = urlfetch.fetch(self.data_url, deadline = 30)
      if result.status_code != 200:
        self.send_error_mail(self.data_url,result)
      return result.content

    def send_error_mail(self,url,result):
      mail.send_mail(sender="ethervoid@gmail.com",
            to="ethervoid@gmail.com",
            subject="Problem updating data ON SOURCE on service mad_traffic! HTTP CODE: %s" %(result.status_code),
            body="URL:%s\n\n\n %s" %(url,result.content))
      logging.info("SOURCE failed: %s" %(url))
      self.response.out.write(result.content)
    
    def delete_old_traffic(self):
      sql = "DELETE FROM mad_traffic_stats"
      self.execute_sql(sql)

    def create_new_traffic(self,list_of_nodes):
      sql = self.create_new_traffic_info_sql(list_of_nodes)
      self.execute_sql(sql)

    def create_new_traffic_info_sql(self,list_of_nodes):
      sql = "INSERT INTO mad_traffic_stats(geohash,status,status_date) VALUES "
      for row in list_of_nodes:
        status = '\'' + row.find('%sstyleUrl' % (self.ns)).text[1:] + '\''
        coordinates = row.find('%sLineString/%scoordinates' % (self.ns,self.ns)).text
        line_string = '\'<LineString><coordinates>' + coordinates + '</coordinates></LineString>\''
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        sql += "(ST_GeoHash(ST_GeomFromKML(%s), 26),%s, to_timestamp('%s','YYYYMMDDHH24MISS'))," % (line_string,status,now)
      sql=sql[:-1]
      return sql

    def execute_sql(self,sql):
      form_fields = {
        'api_key' :'XXXXXXXXX',
        'q'       :sql
      }
      form_data = urllib.urlencode(form_fields)
      urlCartoSql = "http://osm2.cartodb.com/api/v2/sql"
      result = urlfetch.fetch(url=urlCartoSql,
                              payload=form_data,
                              method=urlfetch.POST,
                              deadline = 30,
                              headers={'Content-Type': 'application/x-www-form-urlencoded'})

      if result.status_code != 200:
        self.send_error_mail(urlCartoSql,result)

application = webapp.WSGIApplication([
  ('/bcn_traffic', BcnTrafficCron),
  ('/mad_traffic', MadTrafficCron)
],debug=True)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
