Dynamic web map example: Barcelona Traffic Map 
===============
[![Preview of example visualization](http://jatorre.github.com/bcn_traffic_map/img/readme_header.png)](http://jatorre.github.com/bcn_traffic_map/)


**[Checkout the demo first](http://jatorre.github.com/bcn_traffic_map/ "Demo").**

This little project is a simple demo on how to use [CartoDB](http://www.cartodb.com) to create maps where its data changes often. In this case the data is traffic data from the city of Barcelona, but it could be any other type of data. This is an example for when you have a data source that changes often and you want to have a map embed on a site with the latest data always visible.

This is very simple because CartoDB is a geospatial database online. In CartoDB maps get generated on real time from data, which means that every time the data changes, all maps using that data will change automatically. It is not like you produce a map and publish it, the map is always live, change the data and the map changes.

In order to change the data on CartoDB you can either do it manually through the User Interface, or you can use the APIs to programatically change it. In this example this is what we are doing, every 15min. we go to the source, find out if there is new data, and if there is insert it on CartoDB and consequently the map gets updated. But lets start from the beginning.

Finding the data
---------------------

For this map we got the data from the Barcelona Open Data portal. Particularly from this two sources:
 
 * [Traffic state information by sections](http://w20.bcn.cat/opendata/Detall.aspx?lang=ANG&recurs=TRAMS): This is the webservice where the data is published more or less every 15min. It includes a relation of street segments and with information about the traffic status, from 0 to 6.
 * [Street sections relations of the public road](http://w20.bcn.cat/opendata/Detall.aspx?lang=ANG&recurs=TRANSIT_RELACIO_TRAMS): The actual street segments geometries and information is on this dataset. 

With the second you produce the lines and with the other dataset you decide in what color you paint them. 

The database structure
---------------------
Before explaining how to import the data I want to explain what is going to be our final database structure on CartoDB. We will have two tables: `bcn_traffic_trams` (street segments geometry) and `bcn_traffic_stats` (street segments traffic stats).  

We will import at the beginning `bcn_traffic_trams` and it will stay untouched forever. On the other hand `bcn_traffic_stats` is where we will be storing the status of the traffic so we will be inserting new data every 15min.

This is a very common pattern in GIS, you have one table with geometries, like countries, and another table with data related to those geometries. You might resuse the geoemtries for different maps, so a map is a JOIN between the geometries and snothe table with data about them. Because CartoDB supports all type of JOINS is easy to manage your data this way.


Importing the geometries on CartoDB
---------------------

We are gonna start importing the Street sections relations of the public road in [CartoDB](http://www.cartodb.com). You do that as usually drag and dropping or selecting the file. It will import pretty quickly.

When you look at the file you will see that they are distributing the geometry information about each segment on a funny way on one column. We need to move that information to the_geom so that CartoDB can visualize it. I did it with:

```
UPDATE transit_relacio_trams 
    SET the_geom = ST_Multi(ST_Force_2D(ST_GeomFromEWKT('SRID=4326;LINESTRING('||replace(replace(replace(coordenades,' ','*'),',',' '),'*',',') ||')'))) 
    WHERE coordenades!=''
```
What this SQL does is convert the funny format the coordinates come into WKT that can be uderstood by PostGIS. Also we remove the 3D part of the geometry (ST_Force_2D) and make it Multiline just in case. Some segments given on the file do not have coordinates, so those we dont transform them of course.

After doing that you should be able to go to map and see all the segments display with the default style.

Importing the traffic state data
---------------------

To accomodate this data we created a new empty table using the CartoDB UI and called it `bcn_traffic_stats`. Adding columns and changing the type we end up with a table that has, apart from the normal CartoDB fields, these fields:

 * status (number)
 * status_date (date)
 * status_in_15min (number)
 * tram_id (number)

Now, if you [look at the source](http://www.bcn.cat/transit/dades/dadestrams.dat) dataset where the city publish the information you will see that it follows a similar structure

`tram_id#status_date#status#status_in_15min`

We need a program that will check every 15minutes this URL and insert all this data into CartoDB if there is new data. In the future CartoDB will allow to syncronize with external resources, but for the time being you have to code that yourself. This is what we have built using [AppEngine](https://developers.google.com/appengine/). Why we choosed Appengine? Because is free, we will not need to mantain it and it has support for cron jobs (repetable tasks that can happen automatically). You could probably also use Heroku or some other Application Cloud Services.

Creating an Appengine app is not complicated, follow their instructions and use the code available on the `appengine_cron` folder. It basically consist of 3 files: 

 * app.yaml : It is where you describe your app an routes. We only define one that will initiate the code
 * cron.yaml : Is where we specify that the /bcn_traffic URL should be called every 15min
 * main.py : Where the actual code is. Here is what gets run every 15min.

I am not going to get into much details, the code is pretty self explanatory. Basically we start downloading the data from the remote server (http://www.bcn.cat/transit/dades/dadestrams.dat) and with that data we produce a SQL that we execute in CartoDB through the SQL API. 

There are some other things on that code. For example, if there are probles getting the source data or writing in CartoDB and email is sent to let us know that something went wrong. The other part that might look strange is on the SQL. It might be that the data on the source has not change since last time we checked. We put some condition on the INSERT to ensure we only INSERT the data if it is actually newer. Also you will see that we are doing multiple INSERTs in one single statement. This is way faster to run that executing separately each one. Do not forget to add you api_key to allow for writes into your database.

Finally, we could have decided to not insert the data, but actually just UPDATE with the latest values. That would be ok and will ensure that your CartoDB account do not keep growing infinetely. But by using INSERT int he future we will be able to create visualizations on how the traffic changes over time which can be pretty neat. But if you only want the last status of traffic you would probably be better with just UPDATES.

Ok. So once you have that appengine app up and running, you should see new data getting inserted on the table every 15min more or less.

Creating the visualization
---------------------

We will start creating the visualization on the CartoDB User Interface, and when we are happy with how it looks like we will create a simple html page to host it.

So login to CartoDB and open the `bcn_traffic_stats` table. Go to the map and you will see nothing. Use this SQL

```
SELECT seg.cartodb_id, seg.the_geom_webmercator, stats.status 
FROM bcn_traffic_trams as seg 
  INNER JOIN bcn_traffic_stats as stats ON stats.tram_id=seg.tram 
   AND stats.status_date = (SELECT max(status_date) FROM bcn_traffic_stats)
```

You might not see yet the map because of the CartoCSS, but you will in a minute. Let me explain this SQL first. We are here joining the two tables `bcn_traffic_trams` and `bcn_traffic_stats` using the `tram_id` and `tram` columns. We are selecting the `the_geom_webmercator` from the `bcn_traffic_trams` table and the `status` from `bcn_traffic_stats`.
Fianlly we are setting a condition so that we only get the latest data. Remember that becase we are inserting all new data, not just replacing, we are acccumulating all the historic values, but on the visualization we only want to display the latest.

Now, click on the CSS button and apply the following CartoCSS:

```
#bcn_traffic_trams::glow{
  line-opacity: 1;
  line-width:4;
  line-color: white;
  [zoom<11] {line-width:1.5; }
  [zoom=11] {line-width:2.3; }
  [zoom=12] {line-width:3.2; }
  [zoom=13] {line-width:5.9; }
  [zoom=14] {line-width:7.2; }
  [zoom=15] {line-width:8.8; }
  [zoom>15] {line-width:10; }
  
}

#bcn_traffic_trams::main{
  line-opacity: 1;
  line-width:4;
  [zoom<11] {line-width:1; }
  [zoom=11] {line-width:1.5; }
  [zoom=12] {line-width:2.0; }
  [zoom=13] {line-width:3.5; }
  [zoom=14] {line-width:4.2; }
  [zoom=15] {line-width:5.2; }
  [zoom>15] {line-width:6.5; }


//0 = muy fluido
[ status = 0] {line-color: #30AE00;}

//1 = fluido
[ status = 1] {line-color: #30AE00;}

//2 = denso
[ status = 2] {line-color: #FFD21D;}

//3 = muy denso
[ status = 3] {line-color: #FFD21D;}

//4 = congestion
[ status = 4] {line-color: #9A0505;}

//5 = sin datos
[ status = 5] {line-color: #FFFFFF;}

//6 = cortado
[ status = 6] {
    line-color: #D10000;
    line-dasharray:2,2;}

}
```
This CartoCSS display the data in two ways, one in white to produce a glow effect and then another time depending the status of the traffic. Using this conditional sytling, together with some optimizations for different zoom levels you get the map.

Change the background map to something you like and you should be seeing already the map you wanted.

Embedding the visualization on an external site
---------------------

Now that we have the map lookign good and automatically updating we are going to make use of an existing template to create a microsite. This is just an example, you can ambed this map in many different contests.

The microsite is very simple, check out index.html here in the repository. Apart from HTML here and there the most important part is how we are making use of cartodb.js to embed the vizualization we just created.

```
<script type="text/javascript">
    var viz = cartodb.createVis('map', 'http://osm2.cartodb.com/api/v1/viz/2275/viz.json')
        .done(function(vis, layers) {
            //Update the info about last update
            $("#updatedAtb").text(
                Math.floor((Math.abs(new Date() - new Date(Date.parse(viz.updated_at)))) / (1000*60))
            );                
    });  
</script>
```
We are using the vizjson document that you get on the User Interface when you click on Share this map and then on API. We also check out when the visualization is loaded the time of the last update, is an attribute returned by cartodb.js, and with it calculate the number of minutes since last update. We update finally the value on the HTML to present that infromation to the user.

Conclussion
---------------------

We hope this has given you a good idea of how to use CartoDB power for rendering dynamic data. If you think about it you have now an always updated map of traffic in Barcelona almost for free.

There are a lot of other scenarios where this type of maps apply. For example if you have a transit map for a city. You can design the entire map with all possible options, and then dynamically change the data when a route is closed or the service has changed. The maps on your site will automatically update without having to generate them manually.

In the future CartoDB will allow to perform some of the syncronization operations that we have described here in Appengine directly inside CartoDB. But while this arrives, using some external Application cloud services can be a really cheap and good option.

We hope you have liked this little app and please [contact us](mailto:contact@cartodb.com) in case you have any questions.

CartoDB team.
