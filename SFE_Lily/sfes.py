# set up force field as per usual

from openff.evaluator.forcefield import SmirnoffForceFieldSource

force_field_path = "openff-2.0.0.offxml"
force_field_source = SmirnoffForceFieldSource.from_path(force_field_path)

# set up dataset

from openff.evaluator.datasets import PhysicalPropertyDataSet
dataset = PhysicalPropertyDataSet.from_json("freesolv.json")


dataset._properties = dataset.properties[:1] # shrink to 1 property

# set up dask local cluster etc

import os

from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

calculation_backend = DaskLocalCluster(
    number_of_workers=1,
    resources_per_worker=ComputeResources(
        number_of_threads=1,
        number_of_gpus=1,
        preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
    ),
)
calculation_backend.start()


# set up server

from openff.evaluator.server import EvaluatorServer

evaluator_server = EvaluatorServer(calculation_backend=calculation_backend)
evaluator_server.start(asynchronous=True)


from openff.evaluator.client import EvaluatorClient

evaluator_client = EvaluatorClient()

request, exception = evaluator_client.request_estimate(
    property_set=dataset,
    force_field_source=force_field_source,
    # options=estimation_options,
)

assert exception is None

results, exception = request.results(synchronous=True, polling_interval=30)
assert exception is None

results.estimated_properties.json("estimated_dataset_sfes_lily.json", format=True)