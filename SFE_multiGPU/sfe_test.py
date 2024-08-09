"""
Evaluator workflow to Load and Filter Data Sets, Estimate Data Sets
Applied to calculations of SFE of Water.
"""

# Core Imports & Setup

import os
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("openff.toolkit").setLevel(logging.ERROR)

from openff import toolkit, evaluator

from openff.units import unit

from rdkit import Chem
from rdkit.Chem import FilterCatalog
from openff.evaluator.substances import Component, Substance

# 0) Registering Custom ThermoML Property of Osmotic Coefficient
from openff.evaluator import properties
from openff.evaluator.datasets.thermoml import thermoml_property
from openff.evaluator.datasets import PhysicalProperty, PropertyPhase

@thermoml_property("Osmotic coefficient", supported_phases=PropertyPhase.Liquid)
class OsmoticCoefficient(PhysicalProperty):
    """A class representation of a osmotic coeff property"""

    @classmethod
    def default_unit(cls):
        return unit.dimensionless
    
...

custom_thermoml_props = [
    OsmoticCoefficient,
]

for custom_prop_cls in custom_thermoml_props:    
    setattr(properties, custom_prop_cls.__name__, custom_prop_cls)

# 1) Loading data sets

## Extracting Data from ThermoML or json file 
from openff.evaluator.datasets import PhysicalProperty, PropertyPhase, PhysicalPropertyDataSet
from openff.evaluator.datasets.thermoml import thermoml_property, ThermoMLDataSet

data_set_initial = PhysicalPropertyDataSet.from_json("freesolv.json")

#Getting smiles
def get_func_smiles(initial_data_set):
    subs=list(set(initial_data_set.substances))
    smiles_list=[]

    for i in subs:
        comps=[]
        comps.append(i.components[0].smiles)
        comps.append(i.components[1].smiles)
        for o in comps:
            comps.remove('O')
            [smiles_list.append(y) for y in comps]


    mols_list=[]

    for s in smiles_list:
        m=Chem.MolFromSmiles(s)
        mols_list.append(m)

    all=[]
    alcohols=[]
    aldehydes=[]
    amines=[]
    carboxylics=[]
    halogens=[]
    nitros=[]
    sulf_chlorides=[]
    terminal_alkynes=[]
    other=[]
    both=[]
    
    fc = FilterCatalog.GetFunctionalGroupHierarchy()
    for i in range(len(mols_list)):
        whtv=mols_list[i]
        if not fc.GetMatches(whtv):
            other.append(i)
        else:
            for match in fc.GetMatches(whtv):
                ffg=match.GetDescription()
                all.append(i)
                # print(i,ffg)
                if ffg == 'Amine':
                    amines.append(i)
                elif ffg == 'Alcohol':
                    alcohols.append(i)
                elif ffg == 'Aldehyde':
                    aldehydes.append(i)
                elif ffg == 'CarboxylicAcid':
                    carboxylics.append(i)
                elif ffg == 'Halogen':
                    halogens.append(i)
                elif ffg == 'Nitro':
                    nitros.append(i) 
                elif ffg == 'SulfonylChloride':
                    sulf_chlorides.append(i)
                elif ffg == 'TerminalAlkyne':
                    terminal_alkynes.append(i)       
                if i in amines and i in alcohols:
                    both.append(i)
                    amines.remove(i)
                    alcohols.remove(i)
    

    def get_smiles(func_type):
        smiles=[]

        for x in func_type:
            comp0=subs[x].components[0].smiles
            comp1=subs[x].components[1].smiles
            if comp0 != 'O':
                smiles.append(comp0)
            if comp1 != 'O':
                smiles.append(comp1)
            # smiles.append(comp0) 
            # smiles.append(comp1)
        smiles.append('O')
        return smiles

    smiles_results={}

    smiles_results['all']=get_smiles(all)
    smiles_results['alcohols']=get_smiles(alcohols)
    smiles_results['aldehydes']=get_smiles(aldehydes)
    smiles_results['carboxylics']=get_smiles(carboxylics)
    smiles_results['halogens']=get_smiles(halogens)
    smiles_results['amines']=get_smiles(amines)
    smiles_results['nitros']=get_smiles(nitros)
    smiles_results['sulf_chlorides']=get_smiles(sulf_chlorides)
    smiles_results['terminal_alkynes']=get_smiles(terminal_alkynes)
    smiles_results['both']=get_smiles(both)
    smiles_results['other']=get_smiles(other)

    return smiles_results

smiles_results=get_func_smiles(data_set_initial)

## Filtering data sets
from openff.evaluator.datasets.curation.components.filtering import FilterByPropertyTypes, FilterByPropertyTypesSchema
from openff.evaluator.datasets.curation.components.filtering import FilterBySmiles, FilterBySmilesSchema

# data_set_sfe= FilterByPropertyTypes.apply(
#     data_set_initial, FilterByPropertyTypesSchema(property_types=["SolvationFreeEnergy"]))

data_set_sfe= FilterBySmiles.apply(
    data_set_initial, FilterBySmilesSchema(smiles_to_include=smiles_results['terminal_alkynes']))

## Saving filtered data set to json file
data_set_path = Path('filtered_dataset_sfe_alkynes.json')
data_set_sfe.json(data_set_path, format=True)

# 2) Estimating data sets

## Loading data set and applying FF parameters
from openff.toolkit.typing.engines.smirnoff import forcefield, ForceField
from openff.evaluator.forcefield import SmirnoffForceFieldSource

### load data
data_set_path = Path('filtered_dataset_sfe_alkynes.json')
data_set = PhysicalPropertyDataSet.from_json(data_set_path)

### load FF
force_field_path = "openff-2.1.0.offxml"
force_field_source = SmirnoffForceFieldSource.from_path(force_field_path)

## Defining calculation Schemas
from openff.evaluator.properties import Density, EnthalpyOfMixing, SolvationFreeEnergy
from openff.evaluator.client import RequestOptions

sfe_schema = SolvationFreeEnergy.default_simulation_schema(n_molecules=256)

### Create an options object which defines how the data set should be estimated.
estimation_options = RequestOptions()

### Specify that we only wish to use molecular simulation to estimate the data set.
estimation_options.calculation_layers = ["SimulationLayer"]

### Add our custom schemas, specifying that the should be used by the 'SimulationLayer' estimation_options.add_schema("SimulationLayer", "Density", density_schema)
estimation_options.add_schema("SimulationLayer", "SFE", sfe_schema)

## Launching a Server and Client
from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.client import EvaluatorClient
from openff.evaluator.client import ConnectionOptions

### define client to submit queries
port = 8120
evaluator_client = EvaluatorClient(ConnectionOptions(server_port=port))

### define available / preferred resources
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
resources = ComputeResources(
    number_of_threads=1,
    number_of_gpus=2,
    preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
)

with DaskLocalCluster(number_of_workers=2, resources_per_worker=resources) as calculation_backend:
    ### spin up server
    evaluator_server = EvaluatorServer(calculation_backend=calculation_backend, delete_working_files=False, port=port)
    evaluator_server.start(asynchronous=True)

    ### estimate data set by submitting calculation schemas to newly-created server
    request, exception = evaluator_client.request_estimate(
        property_set=data_set,
        force_field_source=force_field_source,
        options=estimation_options,
    )

    ### Wait for the results.
    results, exception = request.results(synchronous=True, polling_interval=30)
    assert exception is None

    a = results.estimated_properties.json("estimated_dataset_sfe_alkynes.json", format=True)
    print(a)

