# Extracting Data from AspenTech IP21

## Prerequisites

* Please make sure "AspenTech SQLplus" ODBC driver is installed on your local workstation.

## Getting Started

* Select "Add New Connection" from Server drop down or from "Connections" menu.
* Select "aspen-ip21" from "Connection Type" dropdown.
* Set "Connection Name" to a string you can later recognize (i.e. "Ip21-left-wing").
* Leave "Connection String" empty if you plan to select "Server Host" IP or DNS name.
* "Default Group" should be set to a name of the table your tags are stored at, when accessing from SQLplus. (It is usually one of the - `IP_AIDef`, `IP_DIDef`, `IP_CalcDef`).
* Select "ODBC Driver" (most often it would be "AspenTech SQLplus").
* Set "Server Host" to be an IP address or DNS name of the IP21 server.

At this point tags from a specific "Default Group" can be accessed per single connection.
If you'd like to access tags from more than a single group - please create multiple connections.
