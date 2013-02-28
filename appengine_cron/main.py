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
    def get(self):
      urlStr="http://informo.munimadrid.es/informo/tmadrid/intensidades.kml"
      result = urlfetch.fetch(urlStr)
      raw_data = result.content
      xml = etree.fromstring(raw_data)
      self.response.out.write(xml.tag)
      return
      for segment in xml.findall('Placemark'):
        self.response.out.write(segment.find('styleUrl').text)
      

class NycTrafficCron(webapp.RequestHandler):
    def get(self):
      
      #grab the data from the BCN open data site
      urlStr = "http://207.251.86.229/nyc-links-cams/LinkSpeedQuery.txt"
      result = urlfetch.fetch(urlStr)
      if result.status_code != 200:
        logging.error(str(result.content))
        mail.send_mail(sender="jatorre@gmail.com",
            to="jatorre@cartodb.com",
            subject="Problem updating data ON SOURCE on service nyc_traffic! HTTP CODE: %s" %(result.status_code),
            body="URL:%s\n\n\n %s" %(urlStr,result.content))
        logging.info("SOURCE failed: %s" %(urlStr))
        return
      
      
      #raw data from service
      raw_data = result.content    
      
      rows = raw_data.split("\r")

      # remove header
      toss = rows.pop(0)

      sql = "INSERT INTO nyc_traffic_stats(DataAsOf, Id, Speed, TravelTime, Status, linkId, linkPoints, agency, Transcom_id, Borough, LinkName, the_geom) SELECT * FROM ( VALUES "
      for row in rows:

        tram = row.replace("\n", "").replace("'","''").split('"\t"')

        if len(tram)==13:
          # could probably use a regex here :)
          # problem is that coordinate strings can use parentheses with commas between, or just comma delimited lat/lngs with space between
          the_geom = tram[6].replace(')(',' ').replace(', ',',').replace("\n","").replace("  "," ").replace(')','').replace('(','').split(' ')
          i = 0
          while i < len(the_geom):
            # some coordinates are invalid (e.g. 74.23232.4242) , here I toss them
            # also, some coordinates are clearly out of nyc, toss them
            try:
                assert float(the_geom[i].split(',')[0]) > 38
                assert float(the_geom[i].split(',')[0]) < 42
                assert float(the_geom[i].split(',')[1]) > -75
                assert float(the_geom[i].split(',')[1]) < - 71
                i += 1
            except:
                toss = the_geom.pop(i)
          if len(the_geom) > 1:
            the_geom = ['ST_MakePoint(%s, %s)' % (i.split(',')[1],i.split(',')[0]) for i in the_geom]

            the_geom = "ST_Multi(ST_SetSRID(ST_MakeLine(Array[%s]),4326))" % ','.join(the_geom)
            sql += "(to_timestamp('%s','MM/DD/YYYY HH24:MI:SS'),%s,%s,%s,%s,%s,'%s','%s',%s,'%s','%s',%s),"%(tram[4],tram[0][1::],tram[1],tram[2],tram[3],tram[5],tram[8],tram[9],tram[10],tram[11],tram[12][:-1],the_geom)
            status_date=tram[4]
      sql=sql[:-1]
      
      sql+=") as n(DataAsOf, Id, Speed, TravelTime, Status, linkId, linkPoints, agency, Transcom_id, Borough, LinkName,the_geom) "
      sql+="WHERE (SELECT max(DataAsOf) FROM nyc_traffic_stats) < to_timestamp('%s','MM/DD/YYYY HH24:MI:SS')"%(status_date)
      
      self.response.out.write(sql)

      form_fields = {
        'api_key' :'',
        'q'       :sql
      }
      form_data = urllib.urlencode(form_fields)
              
      result = urlfetch.fetch(url="https://osm2.cartodb.com/api/v1/sql",
                              payload=form_data,
                              method=urlfetch.POST,
                              headers={'Content-Type': 'application/x-www-form-urlencoded'})

      #If the call fails send an email to notify that there is a problem with the service
      if result.status_code != 200:
        logging.error(str(result.content))
        mail.send_mail(sender="jatorre@gmail.com",
            to="jatorre@cartodb.com",
            subject="Problem updating data ON CARTODB on service nyc_traffic: "+str(result.content),
            body="URL:"+urlStr +"\n\n\n"+ result.content)
      else:
        logging.error('success')
        


application = webapp.WSGIApplication([
  ('/bcn_traffic', BcnTrafficCron),
  ('/mad_traffic', MadTrafficCron),
  ('/nyc_traffic', NycTrafficCron)
],debug=True)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()