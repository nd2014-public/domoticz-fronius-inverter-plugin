#           Fronius Inverter Plugin
#
#           Author:     ADJ, 2018
#
"""
<plugin key="froniusInverter" name="Fronius Inverter" author="ADJ" version="0.0.1" wikilink="https://github.com/aukedejong/domoticz-fronius-inverter-plugin.git" externallink="http://www.fronius.com">
    <params>
        <param field="Mode1" label="IP Address" required="true" width="200px" />
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
                <option label="Logging" value="File"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import sys
import json
import datetime
import urllib.request
import urllib.error

class BasePlugin:
    inverterWorking = True
    intervalCounter = None
    heartbeat = 30
    previousTotalWh = 0
    previousCurrentWatt = 0
    whFraction = 0

    def onStart(self):
        if Parameters["Mode6"] != "Normal":
            Domoticz.Debugging(1)

        if (len(Devices) == 0):
            Domoticz.Device(Name="House consumption",  Unit=1, TypeName="kWh",Used=1).Create()
            Domoticz.Device(Name="Solar production",  Unit=2, TypeName="kWh", Used=1).Create()
            Domoticz.Device(Name="Energy bought",  Unit=3, TypeName="kWh", Used=1).Create()
            Domoticz.Device(Name="Autonomy rate",  Unit=4, TypeName="Percentage", Used=1).Create()
            logDebugMessage("Devices created.")

        Domoticz.Heartbeat(self.heartbeat)
        self.intervalCounter = 0

        if ('FroniusInverter' not in Images): Domoticz.Image('Fronius Inverter Icons.zip').Create()
        if ('FroniusInverterOff' not in Images): Domoticz.Image('Fronius Inverter Off Icons.zip').Create()

        Devices[1].Update(0, sValue=Devices[1].sValue, Image=Images["FroniusInverter"].ID)
        Devices[2].Update(0, sValue=Devices[2].sValue, Image=Images["FroniusInverter"].ID)
        Devices[3].Update(0, sValue=Devices[3].sValue, Image=Images["FroniusInverter"].ID)
        Devices[4].Update(0, sValue=Devices[4].sValue, Image=Images["FroniusInverter"].ID)
        return True


    def onHeartbeat(self):

        if self.intervalCounter == 1:

            ipAddress = Parameters["Mode1"]
            jsonObject = self.getInverterRealtimeData( ipAddress )

            if (self.isInverterActive(jsonObject)):

                self.updateDeviceCurrent(jsonObject)
                # self.updateDeviceMeter(jsonObject)

                if (self.inverterWorking == False):
                    self.inverterWorking = True

            else:
                self.logErrorCode(jsonObject)

                if (self.inverterWorking == True):
                    self.inverterWorking = False
                    self.updateDeviceOff()


            # self.intervalCounter = 0

        else:
            self.intervalCounter = 1
            #logDebugMessage("Do nothing: " + str(self.intervalCounter))


        return True


    def getInverterRealtimeData(self, ipAddress):

        url = "http://" + ipAddress + "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
        logDebugMessage('Retrieve solar data from ' + url)

        try:
            req = urllib.request.Request(url)
            jsonData = urllib.request.urlopen(req).read()
            jsonObject = json.loads(jsonData.decode('utf-8'))
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logErrorMessage("Error: " + str(e) + " URL: " + url)
            return

        #logDebugMessage("JSON: " + str(jsonData))

        return jsonObject



    def isInverterActive(self, jsonObject):

        return jsonObject["Head"]["Status"]["Code"] == 0


    def logErrorCode(self, jsonObject):

        code = jsonObject["Head"]["Status"]["Code"]
        reason = jsonObject["Head"]["Status"]["Reason"]
        if (code != 12):
            logErrorMessage("Code: " + str(code) + ", reason: " + reason)

        return


    def updateDeviceCurrent(self, jsonObject):

        SolarProduction = round(jsonObject["Body"]["Data"]["Inverters"]["1"]["P"])
        EnergyBought = round(jsonObject["Body"]["Data"]["Site"]["P_Grid"])

        logDebugMessage("Solar prod :" + str(SolarProduction) + ", bought : " + str(EnergyBought))

        HouseConsumption = SolarProduction + EnergyBought
        
        AutonomyRate = 100
        if (HouseConsumption > SolarProduction):
            AutonomyRate = round((SolarProduction / HouseConsumption) * 100)

        Devices[1].Update(HouseConsumption, str("0"))
        Devices[2].Update(SolarProduction, str("0"))
        Devices[3].Update(EnergyBought, str("0"))
        Devices[4].Update(AutonomyRate, str("0"))

        return

    def updateDeviceMeter(self, jsonObject):
        totalWh = jsonObject["Body"]["Data"]["TOTAL_ENERGY"]["Value"]
        currentWatts = jsonObject["Body"]["Data"]["PAC"]["Value"]

        if (self.previousTotalWh < totalWh):
            logDebugMessage("New total recieved: prev:" + str(self.previousTotalWh) + " - new:" + str(totalWh) + " - last faction: " + str(self.whFraction))
            self.whFraction = 0
            self.previousTotalWh = totalWh

        else:
            averageWatts =  (self.previousCurrentWatt + currentWatts) / 2
            self.whFraction = self.whFraction + int(round(averageWatts / 60))
            logDebugMessage("Fraction calculated: " + str(currentWatts) + " - " + str(self.whFraction))


        self.previousCurrentWatt = currentWatts
        calculatedWh = totalWh + self.whFraction
        Devices[2].Update(0, str(currentWatts) + ";" + str(calculatedWh))

        return


    def updateDeviceOff(self):

        Devices[1].Update(0, "0", Images["FroniusInverterOff"].ID)
        Devices[2].Update(0, "0", Images["FroniusInverterOff"].ID)
        Devices[3].Update(0, "0", Images["FroniusInverterOff"].ID)
        Devices[4].Update(0, "0", Images["FroniusInverterOff"].ID)

        # calculatedWh = self.previousTotalWh + self.whFraction
        # Devices[2].Update(0, "0;" + str(calculatedWh))


    def onStop(self):
        logDebugMessage("onStop called")
        return True

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def logDebugMessage(message):
    if (Parameters["Mode6"] == "Debug"):
        now = datetime.datetime.now()
        f = open(Parameters["HomeFolder"] + "fronius-inverter-plugin.log", "a")
        f.write("DEBUG - " + now.isoformat() + " - " + message + "\r\n")
        f.close()
    Domoticz.Debug(message)

def logErrorMessage(message):
    if (Parameters["Mode6"] == "Debug"):
        now = datetime.datetime.now()
        f = open(Parameters["HomeFolder"] + "fronius-inverter-plugin.log", "a")
        f.write("ERROR - " + now.isoformat() + " - " + message + "\r\n")
        f.close()
    Domoticz.Error(message)
