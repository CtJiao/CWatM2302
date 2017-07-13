# -------------------------------------------------------------------------
# Name:        Routing module - Kinematic wave
# Purpose:
#
# Author:      PB
#
# Created:     17/01/2017
# Copyright:   (c) PB 2017
# -------------------------------------------------------------------------

from management_modules.data_handling import *
from hydrological_modules.routing_reservoirs.routing_sub import *
from hydrological_modules.lakes_reservoirs import *



class routing_kinematic(object):

    """
    ROUTING
    routing using the kinematic wave

    """

    def __init__(self, routing_kinematic_variable):
        self.var = routing_kinematic_variable
        self.lakes_reservoirs_module = lakes_reservoirs(self.var)


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the routing module

        * load and create a river network
        * calculate river network parameter e.g. river length, width, depth, gradient etc.
        * calculate initial filling
        * calculate manning's roughness coefficient
        """

        ldd = loadmap('Ldd')
        self.var.lddCompress, dirshort, self.var.dirUp, self.var.dirupLen, self.var.dirupID, self.var.downstruct, self.var.catchment, self.var.dirDown, self.var.lendirDown = defLdd2(ldd)

        #self.var.ups = upstreamArea(dirDown, dirshort, self.var.cellArea)
        self.var.UpArea1 = upstreamArea(self.var.dirDown, dirshort, globals.inZero + 1.0)
        self.var.UpArea = upstreamArea(self.var.dirDown, dirshort, self.var.cellArea)
        d1 =downstream1(self.var.dirUp, self.var.UpArea1)
        up1 = upstream1( self.var.downstruct,self.var.UpArea1)

        ii =1

        #lib2.kinematic(Qold, q, dd, dl, di, Qnew, alpha, 0.6, deltaT, deltaX, len(dirDown))
        #lib2.kinematic(Qold, q, self.var.dirDown, self.var.dirupLen, self.var.dirupID, Qnew, alpha, 0.6, deltaT, deltaX, self.var.lendirDown)

        #---------------------------------------------------------------
        #Calibration
        # mannings roughness factor 0.1 - 10.0
        manningsFactor = loadmap('manningsN')


        # number of substep per day
        self.var.noRoutingSteps = int(loadmap('NoRoutingSteps'))
        # kinematic wave parameter: 0.6 is for broad sheet flow
        self.var.beta = loadmap('chanBeta')
        # Channel Manning's n
        self.var.chanMan = loadmap('chanMan') * manningsFactor
        # Channel gradient (fraction, dy/dx)
        self.var.chanGrad = np.maximum(loadmap('chanGrad'), loadmap('chanGradMin'))
        # Channel length [meters]
        self.var.chanLength = loadmap('chanLength')
        # Channel bottom width [meters]
        self.var.chanWidth = loadmap('chanWidth')

        # Bankfull channel depth [meters]
        self.var.chanDepth = loadmap('chanDepth')



        #-----------------------------------------------
        # Inverse of beta for kinematic wave
        self.var.invbeta = 1 / self.var.beta
        # Inverse of channel length [1/m]
        self.var.invchanLength = 1 / self.var.chanLength

        # Corresponding sub-timestep (seconds)
        self.var.dtRouting = self.var.DtSec / self.var.noRoutingSteps
        self.var.invdtRouting = 1 / self.var.dtRouting

        # -----------------------------------------------
        # ***** CHANNEL GEOMETRY  ************************************

        # Area (sq m) of bank full discharge cross section [m2]
        self.var.totalCrossSectionAreaBankFull = self.var.chanDepth * self.var.chanWidth
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)
        #TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull
        # TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        self.var.totalCrossSectionArea =  0.5 * self.var.totalCrossSectionAreaBankFull
        # Total cross-sectional area [m2]: if initial value in binding equals -9999 the value at half bankfull is used,

        # -----------------------------------------------
        # ***** CHANNEL ALPHA (KIN. WAVE)*****************************
        # ************************************************************
        # Following calculations are needed to calculate Alpha parameter in kinematic
        # wave. Alpha currently fixed at half of bankful depth

        # Reference water depth for calculation of Alpha: half of bankfull
        #chanDepthAlpha = 0.5 * self.var.chanDepth
        # Channel wetted perimeter [m]
        self.var.chanWettedPerimeterAlpha = self.var.chanWidth + 2 * 0.5 * self.var.chanDepth

        # ChannelAlpha for kinematic wave
        alpTermChan = (self.var.chanMan / (np.sqrt(self.var.chanGrad))) ** self.var.beta
        self.var.alpPower = self.var.beta / 1.5
        self.var.channelAlpha = alpTermChan * (self.var.chanWettedPerimeterAlpha ** self.var.alpPower) *2.5
        self.var.invchannelAlpha = 1. / self.var.channelAlpha

        # -----------------------------------------------
        # ***** CHANNEL INITIAL DISCHARGE ****************************

        # channel water volume [m3]
        # Initialise water volume in kinematic wave channels [m3]
        channelStorageIni = self.var.totalCrossSectionArea * self.var.chanLength * 0.2
        self.var.channelStorage = self.var.init_module.load_initial("channelStorage", default = channelStorageIni)

        # Initialise discharge at kinematic wave pixels (note that InvBeta is
        # simply 1/beta, computational efficiency!)
        #self.var.chanQKin = np.where(self.var.channelAlpha > 0, (self.var.totalCrossSectionArea / self.var.channelAlpha) ** self.var.invbeta, 0.)
        dischargeIni = (self.var.channelStorage * self.var.invchanLength * self.var.invchannelAlpha) ** (self.var.invbeta)
        self.var.discharge = self.var.init_module.load_initial("discharge", default=dischargeIni)
        #self.var.chanQKin = chanQKinIni

        #self.var.riverbedExchange = globals.inZero.copy()
        self.var.riverbedExchange = self.var.init_module.load_initial("riverbedExchange")
        #self.var.discharge = self.var.chanQKin.copy()

        ii =1

        #self.var.channelAlphaPcr = decompress(self.var.channelAlpha)
        #self.var.chanLengthPcr = decompress(self.var.chanLength)

        self.var.timestepsToAvgDischarge = globals.inZero.copy()

        if checkOption('sumWaterBalance'):
            self.var.catchmentAll = loadmap('Catchment').astype(np.int)
            self.var.catchmentNo = int(loadmap('CatchmentNo'))

            lddnp = loadmap('Ldd')
            # all last outflow points are marked
            self.var.outlets = np.where(lddnp ==5, self.var.catchmentAll, 0)
            ii =1






    # --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the routing module

        * calculate evaporation from channels
        * calcualte riverbed exchange between riverbed and groundwater
        * if option **waterbodies** is true, calculate retention from water bodies
        * calculate sideflow -> inflow to river
        * calcculate kinematic wave -> using C++ library for computational speed
        """

        #   if option['PCRaster']: from pcraster.framework import *

# ---------------------------------------------------------------------------------



        # if routing is not needed return
        if not(checkOption('includeRouting')):
            return

        if checkOption('calcWaterBalance'):
            self.var.prechannelStorage = self.var.channelStorage.copy()
            #preRes = globals.inZero.copy()
            #np.put(preRes,self.var.decompress_LR,self.var.reservoirStorageM3C)
            #self.var.preRes = self.var.reservoirStorageM3C.copy()




        Qnew = globals.inZero.copy()

        # Evaporation from open channel
        # from big lakes/res and small lakes/res is calculated separately
        channelFraction = np.minimum(1.0, self.var.chanWidth * self.var.chanLength / self.var.cellArea)

        self.var.EvaAddM =  (self.var.EWRef - self.var.openWaterEvap[5]) * channelFraction * self.var.cellArea
        self.var.EvaAddM = np.where((0.95 * self.var.channelStorage - self.var.EvaAddM) > 0.0, self.var.EvaAddM, 0.95 * self.var.channelStorage)



        # riverbed infiltration (m3):
        # - current implementation based on Inge's principle (later, will be based on groundater head (MODFLOW) and can be negative)
        # - happening only if 0.0 < baseflow < nonFossilGroundwaterAbs
        # - infiltration rate will be based on aquifer saturated conductivity
        # - limited to fracWat
        # - limited to available channelStorage
        # - this infiltration will be handed to groundwater in the next time step

        # used self.var.fracVegCover[5] instead of self.var.dynamicFracWat
        self.var.riverbedExchange = np.maximum(0.0,  np.minimum(self.var.channelStorage,\
                                np.where(self.var.baseflow > 0.0, \
                                np.where(self.var.nonFossilGroundwaterAbs > self.var.baseflow, \
                                self.var.kSatAquifer * self.var.fracVegCover[5] * self.var.cellArea, \
                                0.0), 0.0)))
        # to avoid flip flop
        self.var.riverbedExchange = np.minimum(self.var.riverbedExchange, 0.95 * self.var.channelStorage)

        if checkOption('includeWaterBodies'):
            # ------------------------------------------------------------
            # evaporation from water bodies (m3), will be limited by available water in lakes and reservoirs
            # calculate outflow from lakes and reservoirs
            #eWaterBody = np.maximum(0.0, (self.var.EWRef) * self.var.lakeArea) / self.var.noRoutingSteps
            eWaterBody = np.maximum(0.0, (self.var.EWRef - self.var.openWaterEvap[5]) * self.var.lakeArea) / self.var.noRoutingSteps
            self.var.evapWaterBodyC = np.compress(self.var.compress_LR, eWaterBody)

            self.var.EvaAddM = np.where(self.var.waterBodyID > 0, 0.,self.var.EvaAddM)
            self.var.riverbedExchange = np.where(self.var.waterBodyID > 0, 0., self.var.riverbedExchange)
        EvaAddM3Dt = self.var.EvaAddM / self.var.noRoutingSteps
        riverbedExchangeDt = self.var.riverbedExchange / self.var.noRoutingSteps




        # ------------------------------------------------------
        # ***** SIDEFLOW **************************************

        runoffM3 = self.var.runoff * self.var.cellArea / self.var.noRoutingSteps


    #    sideflowChanM3 -= self.var.sum_actSurfaceWaterAbstract * self.var.cellArea
        # return flow from (m) non irrigation water demand
    #    self.var.nonIrrReturnFlow = self.var.nonIrrReturnFlowFraction * self.var.nonIrrGrossDemand
    #    sideflowChanM3 +=  self.var.nonIrrReturnFlow * self.var.cellArea
        #sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.invdtRouting

        # ************************************************************
        # ***** KINEMATIC WAVE                        ****************
        # ************************************************************

        #sideflowChan = sideflowChan / self.var.noRoutingSteps
        for subrouting in xrange(self.var.noRoutingSteps):

            sideflowChanM3 = runoffM3.copy()
            # minus evaporation from channels
            sideflowChanM3 -= EvaAddM3Dt
            # minus riverbed exchange
            #sideflowChanM3 -= riverbedExchangeDt

            if checkOption('includeWaterBodies'):
                lakesResOut = self.lakes_reservoirs_module.dynamic_inloop(subrouting)
                sideflowChanM3 += lakesResOut




            #sideflowChan = sideflowChanM3 * self.var.invchanLength * self.var.InvDtSec
            sideflowChan = sideflowChanM3 * self.var.invchanLength * 1/ self.var.dtRouting

            if checkOption('includeWaterBodies'):
               lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown_LR, self.var.dirupLen_LR, self.var.dirupID_LR, Qnew, self.var.channelAlpha, 0.6, self.var.dtRouting, self.var.chanLength, self.var.lendirDown_LR)

            else:
               lib2.kinematic(self.var.discharge, sideflowChan, self.var.dirDown, self.var.dirupLen, self.var.dirupID, Qnew, self.var.channelAlpha, 0.6, self.var.dtRouting, self.var.chanLength, self.var.lendirDown)
            self.var.discharge = Qnew.copy()



        # -- end substeping ---------------------

        self.var.channelStorage = self.var.channelAlpha * self.var.chanLength * Qnew ** 0.6


        """
        if checkOption('calcWaterBalance'):
            self.var.waterbalance_module.waterBalanceCheckSum(
                [runoffM3, lakesResOut],            # In
                [sideflowChanM3, EvaAddM3Dt],           # Out
                [ ],                                  # prev storage
                [],
                "Routing1", True)

        if checkOption('calcWaterBalance'):
            Res = globals.inZero.copy()
            np.put(Res, self.var.decompress_LR, self.var.reservoirStorageM3C)
            self.var.waterbalance_module.waterBalanceCheckSum(
                [runoffM3,lakesResOut,eWaterBody],            # In
                [sideflowChanM3, EvaAddM3Dt  ],           # Out
                [preRes],                                  # prev storage
                [Res],
                "Routing2", False)
        """

        self.var.channelStorageBefore = self.var.channelStorage.copy()


        #if checkOption('PCRaster'): report(decompress(self.var.discharge), "C:\work\output2/q1.map")






        """
        a = readmap("C:\work\output/q_pcr")
        b = nominal(a*100)
        c = ifthenelse(b == 105779, scalar(9999), scalar(0))
        report(c,"C:\work\output/t3.map")
        d = compressArray(c)
        np.where(d == 9999)   #23765
        e = pcr2numpy(c, 0).astype(np.float64)
        np.where(e > 9000)   # 75, 371  -> 76, 372
        """


