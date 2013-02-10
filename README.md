Dynamically web maps example: Barcelona Traffic Map 
===============

[Checkout the demo first](http://jatorre.github.com/bcn_traffic_map/ "Demo").

This little project is a simple demo on how to use [CartoDB](http://www.cartodb.com) to create maps where its data changes often. In thie case the data is the traffic data from the city of Barcelona, but it could be any other type of data. This is an example for when you have a data source that changes often and you want to have a map embed on a site with the latest data always visible.

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

We need a program that will check every 15minutes this URL and insert all this data into CartoDB if there is new data. In the future CartoDB will allow to syncronize with external resources, but for the time being you have to code that yourself. This is what we have built using [AppEngine](https://developers.google.com/appengine/). Why we choosed Appengine? Because is free, we will not need to mantain it and it has support for cron jobs (repetable tasks that can happen automtically).






