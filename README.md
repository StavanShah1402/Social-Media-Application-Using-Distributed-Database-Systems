# Social-Media-Application-Using-Distributed-Database-Systems

**Social Media Database with MongoDB and Docker**

This project sets up a sharded MongoDB cluster using Docker to handle a scalable and distributed database for a social media platform. Below, you will find instructions to explore the application and replicate the database setup on your local system.

**Table of Contents**
1.	Prerequisites
2.	UI Setup
3.	Database Replication using Docker
     o	Config Server Replica Set
     o	Router Setup
     o	Shard Replica Sets
4.	Sharding and Indexing
5.	Connect and Explore


**Prerequisites**

•	Python 3.x
•	Docker Desktop (Download here)
•	A basic understanding of MongoDB concepts such as sharding, replica sets, and config servers.


**UI Setup**
To have a look at your UI 
1.	Connect to the MongoDB Cluster
Use the following connection URL to connect to our single cluster MongoDB:
    mongodb+srv://test1234:test1234@cluster0.wsbge.mongodb.net/
2.	Run the Python Application
    python app.py


**Database Replication Using Docker**
Step 1: Config Server Replica Set
1.	Create a custom Docker network for the MongoDB cluster:
         docker network create mongo_cluster_network
2.	Run three config servers:
       docker run -d --name mongo1 --net mongo_cluster_network -p 27018:27018 \-v     
       /var/lib/docker/volumes/mongo1_data/_data:/data/configdb \mongo:6.0 mongod --          configsvr --replSet rs0 -- 
       bind_ip_all --port 27018 --dbpath /data/configdb
  	
       docker run -d --name mongo2 --net mongo_cluster_network -p 27019:27019 \-v /var/lib/docker/volumes/mongo2_data/_data:/data/configdb \mongo:6.0 mongod --    configsvr --replSet rs0 --    
        bind_ip_all --port 27019 --dbpath /data/configdb

       docker run -d --name mongo3 --net mongo_cluster_network -p 27020:27020 \
       -v /var/lib/docker/volumes/mongo3_data/_data:/data/configdb \mongo:6.0 mongod --configsvr --replSet rs0 --      
       bind_ip_all --port 27020 --dbpath /data/configdb

4.	Connect to any one of the servers and initialize the replica set:
            rs.initiate({
                      _id: "rs0",
                      configsvr: true,
                       members: [
{id: 0, host: "mongo1:27018"},
{id: 1, host: "mongo2:27019"},
{id: 2, host: "mongo3:27020"}
]
                });


**Step 2: Router Setup**
Set up a MongoDB Router (mongos) to manage requests and distribute them across shards.
          docker run -d --name mongos \net mongo_cluster_network \p 27017:27017 \mongo:6.0 mongos --configdb             
          rs0/mongo1:27018,mongo2:27019,mongo3:27020


**Step 3: Shard Replica Sets**
1.	Create multiple shard replica sets:
For Shard 1:
    docker run -d --name shard1a --net mongo_cluster_network -p 27021:27021 \
    -v /var/lib/docker/volumes/shard1a_data:/data/db mongo:6.0 mongod --shardsvr --replSet shard1ReplSet --bind_ip_all --       port 27021

    docker run -d --name shard1b --net mongo_cluster_network -p 27022:27022 \
    -v /var/lib/docker/volumes/shard1b_data:/data/db mongo:6.0 mongod --shardsvr --replSet shard1ReplSet --bind_ip_all --       port 27022

    docker run -d --name shard1c --net mongo_cluster_network -p 27023:27023 \
    -v /var/lib/docker/volumes/shard1c_data:/data/db mongo:6.0 mongod --shardsvr --replSet shard1ReplSet --bind_ip_all --       port 27023
  	
Repeat similar commands for Shard 2 and Shard 3, using different ports and names (e.g., shard2a, shard2b, etc.).

3.	Configure each shard's replica set by connecting to one member of each set and executing:
      rs.initiate({
   			      id: "shard1ReplSet",
   			       members: [
{ _id: 0, host: "shard1a:27021" },
{ _id: 1, host: "shard1b:27022" },
{ _id: 2, host: "shard1c:27023" }
]
 });


**Step 4: Connect Shards to the Router**
Connect all shards to the mongos router:
    sh.addShard("shard1ReplSet/shard1a:27021,shard1b:27022,shard1c:27023");
    sh.addShard("shard2ReplSet/shard2a:27031,shard2b:27032,shard2c:27033");
    sh.addShard("shard3ReplSet/shard3a:27041,shard3b:27042,shard3c:27043");



**Sharding and Indexing**
1.	Create indexes for shard keys:
   db.users.createIndex({ geographic_location: 1 });
2.	Enable sharding for collections:
   sh.shardCollection("socialMedia.users", { geographic_location: 1 });
   sh.shardCollection("socialMedia.comments", { post_id: 1 });
   sh.shardCollection("socialMedia.posts", { user_id: 1, timestamp: 1 });
   sh.shardCollection("socialMedia.messages", { receiver_id: 1, sender_id: 1 });


**Connect and Explore**
1.	Use the mongos router to interact with your sharded MongoDB cluster. Example connection string for mongo shell:
    mongo --host localhost --port 27017

2.	Run your application and explore the database functionality.

