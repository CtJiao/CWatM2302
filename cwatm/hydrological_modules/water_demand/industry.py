from cwatm.management_modules import globals
import numpy as np
from cwatm.management_modules.data_handling import returnBool, binding, cbinding, loadmap, readnetcdf2, divideValues

class waterdemand_industry:
    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        if "industryTimeMonthly" in binding:
            if returnBool('industryTimeMonthly'):
                self.var.industryTime = 'monthly'
            else:
                self.var.industryTime = 'yearly'
        else:
            self.var.industryTime = 'monthly'

        if "industryWithdrawalvarname" in binding:
            self.var.indWithdrawalVar = cbinding("industryWithdrawalvarname")
        else:
            self.var.indWithdrawalVar = "industryGrossDemand"
        if "industryConsuptionvarname" in binding:
            self.var.indConsumptionVar = cbinding("industryConsuptionvarname")
        else:
            self.var.indConsumptionVar = "industryNettoDemand"

    def dynamic(self):
            if self.var.industryTime == 'monthly':
                new = 'newMonth'
            else:
                new = 'newYear'

            if globals.dateVar['newStart'] or globals.dateVar[new]:
                self.var.industryDemand = readnetcdf2('industryWaterDemandFile', globals.dateVar['currDate'], self.var.industryTime, value=self.var.indWithdrawalVar)
                self.var.pot_industryConsumption = readnetcdf2('industryWaterDemandFile', globals.dateVar['currDate'], self.var.industryTime, value=self.var.indConsumptionVar)
                self.var.industryDemand = np.where(self.var.industryDemand > self.var.InvCellArea, self.var.industryDemand, 0.0)
                self.var.pot_industryConsumption = np.where(self.var.pot_industryConsumption > self.var.InvCellArea, self.var.pot_industryConsumption, 0.0)
                self.var.ind_efficiency = divideValues(self.var.pot_industryConsumption, self.var.industryDemand)

                # transform from mio m3 per year (or month) to m/day if necessary
                if not self.var.demand_unit:
                    if self.var.industryTime == 'monthly':
                        timediv= globals.dateVar['daysInMonth']
                    else:
                        timediv = globals.dateVar['daysInYear']
                    self.var.industryDemand = self.var.industryDemand * 1000000 * self.var.M3toM / timediv
                    self.var.pot_industryConsumption = self.var.pot_industryConsumption * 1000000 * self.var.M3toM / timediv