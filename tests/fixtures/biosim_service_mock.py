import uuid

from typing_extensions import override

from biosim_server.common.biosim1_client import BiosimService, Hdf5DataValues, BiosimSimulationRun, HDF5File, \
    BiosimSimulationRunStatus, BiosimSimulatorSpec
from biosim_server.common.database.data_models import BiosimulatorVersion


class ObjectNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class BiosimServiceMock(BiosimService):
    sim_runs: dict[str, BiosimSimulationRun] = {}
    hdf5_files: dict[str, HDF5File] = {}
    hdf5_data: dict[str, dict[str, Hdf5DataValues]] = {}

    def __init__(self,
                 sim_runs: dict[str, BiosimSimulationRun] | None = None,
                 hdf5_files: dict[str, HDF5File] | None = None,
                 hdf5_data: dict[str, dict[str, Hdf5DataValues]] | None = None) -> None:
        if sim_runs:
            self.sim_runs = sim_runs
        if hdf5_files:
            self.hdf5_files = hdf5_files
        if hdf5_data:
            self.hdf5_data = hdf5_data

    @override
    async def get_sim_run(self, simulation_run_id: str) -> BiosimSimulationRun:
        sim_run = self.sim_runs[simulation_run_id]
        if sim_run:
            return sim_run
        else:
            raise ObjectNotFoundError("Simulation run not found")

    @override
    async def run_biosim_sim(self, local_omex_path: str, omex_name: str, simulator_spec: BiosimSimulatorSpec) -> BiosimSimulationRun:
        sim_id = str(uuid.uuid4())
        sim_run = BiosimSimulationRun(
            id=sim_id,
            name=omex_name,
            simulator=simulator_spec.simulator,
            simulatorVersion=simulator_spec.version or "1.0",
            simulatorDigest="sha256:5d1595553608436a2a343f8ab7e650798ef5ba5dab007b9fe31cd342bf18ec81",
            status=BiosimSimulationRunStatus.RUNNING
        )
        self.sim_runs[sim_id] = sim_run
        return sim_run

    @override
    async def get_hdf5_metadata(self, simulation_run_id: str) -> HDF5File:
        hdf5_file = self.hdf5_files[simulation_run_id]
        if hdf5_file:
            return hdf5_file
        else:
            raise ObjectNotFoundError("HDF5 metadata not found")

    @override
    async def get_hdf5_data(self, simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
        all_hdf5_values: dict[str, Hdf5DataValues] = self.hdf5_data[simulation_run_id]
        if all_hdf5_values:
            return all_hdf5_values[dataset_name]
        else:
            raise ObjectNotFoundError("HDF5 metadata not found")

    @override
    async def get_simulation_versions(self) -> list[BiosimulatorVersion]:
        sim_versions_ndjson: str = \
        """
        {"id":"ginsim","name":"GINsim","version":"3.0.0b","image":{"url":"ghcr.io/biosimulators/ginsim:3.0.0b","digest":"sha256:7b884d0a7d44a157d0e1a4e066ec15b70f8550c664e73c626f79760a82b9b538"}}
        {"id":"boolnet","name":"BoolNet","version":"2.1.5","image":{"url":"ghcr.io/biosimulators/boolnet:2.1.5","digest":"sha256:4a9c10d923b25d4d2e7c729a18d2c3a19ab56203e76a3f9bc935e24c4f197929"}}
        {"id":"cbmpy","name":"CBMPy","version":"0.7.25","image":{"url":"ghcr.io/biosimulators/cbmpy:0.7.25","digest":"sha256:95cf691064e447052c4277a950aa7584afa4f9888e9ce77e68b485449889f307"}}
        {"id":"libsbmlsim","name":"LibSBMLSim","version":"1.4.0","image":{"url":"ghcr.io/biosimulators/libsbmlsim:1.4.0","digest":"sha256:c5cbaf7d68b10d252bf433909606f84dfd6da9bb139d889bb9cbc0a759c6033f"}}
        {"id":"rbapy","name":"RBApy","version":"1.0.2","image":{"url":"ghcr.io/biosimulators/rbapy:1.0.2","digest":"sha256:ba864d2add5b444da6fbbc274b4eb633963e9c677b686c602efb6610b10d1ec3"}}
        {"id":"netpyne","name":"NetPyNe","version":"1.0.0.2","image":{"url":"ghcr.io/biosimulators/netpyne:1.0.0.2","digest":"sha256:7b379580e509151589a34fc398f77c9bb2e33b7c460e9ac74db98798328f0547"}}
        {"id":"neuron","name":"NEURON","version":"8.0.0","image":{"url":"ghcr.io/biosimulators/neuron:8.0.0","digest":"sha256:423142e072688a52b0d7d58073b91dc4d9f6fd4cd7b75d9259c10ef89c276f7c"}}
        {"id":"xpp","name":"XPP","version":"8.0","image":{"url":"ghcr.io/biosimulators/xpp:8.0","digest":"sha256:b8e41eb7175de41d3bfcf1ff5679389e12af4350a4cdcbc56caa4ed52f3b64f0"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.67","image":{"url":"ghcr.io/biosimulators/smoldyn:2.67","digest":"sha256:763d25a0dac503231a541ed18e7fabd19728b4c3d11d9d378297d5f776477c08"}}
        {"id":"copasi","name":"COPASI","version":"4.34.251","image":{"url":"ghcr.io/biosimulators/copasi:4.34.251","digest":"sha256:d3331edfa2f0d8c51a28e57543ecc59d537bf5a7d557652c455cf57a6d23a08b"}}
        {"id":"cobrapy","name":"COBRApy","version":"0.22.1","image":{"url":"ghcr.io/biosimulators/cobrapy:0.22.1","digest":"sha256:55fb3d94a2abeb72cef904abe8dc71fc82744962081916e15536812ad2baba62"}}
        {"id":"pysces","name":"PySceS","version":"1.0.0","image":{"url":"ghcr.io/biosimulators/pysces:1.0.0","digest":"sha256:cb9bf5ce922c6a9595d9d0f632eba66c343fd3477e9119eccbaf47b50a4b64bf"}}
        {"id":"bionetgen","name":"BioNetGen","version":"2.7.0","image":{"url":"ghcr.io/biosimulators/bionetgen:2.7.0","digest":"sha256:db5314da674b51f02f0339c3bf90b85d91d530182f6b92a7ca6bd6527ce6425c"}}
        {"id":"opencor","name":"OpenCOR","version":"2021-10-05","image":{"url":"ghcr.io/biosimulators/opencor:2021-10-05","digest":"sha256:9a575dca3a0d2c0fba4b1d299484d272a5c496353811423030c6082cda8e7036"}}
        {"id":"tellurium","name":"tellurium","version":"2.2.1","image":{"url":"ghcr.io/biosimulators/tellurium:2.2.1","digest":"sha256:2464aa62d911f99e7cfae07de73ac21eb6bc94fdaf5a65813c465616e2c72a01"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.26","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.26","digest":"sha256:9777aa903ee1cde473fcdf2121679d5f4425a90b175db45385c35171dbeeda6f"}}
        {"id":"pyneuroml","name":"pyNeuroML","version":"0.5.18","image":{"url":"ghcr.io/biosimulators/pyneuroml:0.5.18","digest":"sha256:c9b3ffd354ee53feb908e1bc41c2305a741d74bfd2fb75b115da59f469d406d8"}}
        {"id":"brian2","name":"Brian 2","version":"2.5.0.1","image":{"url":"ghcr.io/biosimulators/brian2:2.5.0.1","digest":"sha256:7886dbb7d524c2fbe5bde4dc8b8613af50b3aa29283d57cf5a20ea6b256c8380"}}
        {"id":"gillespy2","name":"GillesPy2","version":"1.6.6","image":{"url":"ghcr.io/biosimulators/gillespy2:1.6.6","digest":"sha256:e024021c3ac4f7ad70793ceb487c98b80da17356a286a22610c092a2d8973199"}}
        {"id":"amici","name":"AMICI","version":"0.11.22","image":{"url":"ghcr.io/biosimulators/amici:0.11.22","digest":"sha256:5f18fee43188b0b4afe17373492e2b7862901fd6f22304f0b052d494ff83fb1c"}}
        {"id":"masspy","name":"MASSpy","version":"0.1.5","image":{"url":"ghcr.io/biosimulators/masspy:0.1.5","digest":"sha256:707acbb88a1874204846f3090988f114232b082796ae9c81e2633f4da4cfb2df"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.67.1","image":{"url":"ghcr.io/biosimulators/smoldyn:2.67.1","digest":"sha256:aa38507d6aff9ceb7d227b5dbd7b07c87839d2cb9f97fce66afc4589530a66d2"}}
        {"id":"amici","name":"AMICI","version":"0.11.23","image":{"url":"ghcr.io/biosimulators/amici:0.11.23","digest":"sha256:7ab1bf4960bf8e22097d2269a86ad33d98a6229498382ab6628ea25095fe2c5e"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.67.2","image":{"url":"ghcr.io/biosimulators/smoldyn:2.67.2","digest":"sha256:abc34e2573d90ec5424b141a0a5f3814ac2619c5c0e69a1168b58bda8cace366"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.33","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.33","digest":"sha256:60681afa6b8ed5728d0a450e04f770ce7d93ecf78548e262f60984fa924c8630"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.34","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.34","digest":"sha256:7a3c3c5a735f6f432801b384f4cf345f1bbf1f2a739ece11e46864b9783ad9a3"}}
        {"id":"amici","name":"AMICI","version":"0.11.24","image":{"url":"ghcr.io/biosimulators/amici:0.11.24","digest":"sha256:92b2116a6e2f5fcd08bcde61d0a8e83710b27a5880978e63abb3ef17e9cbff6d"}}
        {"id":"amici","name":"AMICI","version":"0.11.25","image":{"url":"ghcr.io/biosimulators/amici:0.11.25","digest":"sha256:8d25d3ead8f8c134ffc3d306b447bc05821ecf0ecd1fc2cf57e6c09831772fe0"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.37","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.37","digest":"sha256:814fb1ef97f448280b5db024eeaa594c97bce7e4d2ab5982cb075ee630813e5f"}}
        {"id":"neuron","name":"NEURON","version":"8.0.2","image":{"url":"ghcr.io/biosimulators/neuron:8.0.2","digest":"sha256:0b7f8ddd450d0cb22e915704247eb20bb24889ec6120f0d6b0ec3f1a6e6193e0"}}
        {"id":"pyneuroml","name":"pyNeuroML","version":"0.5.20","image":{"url":"ghcr.io/biosimulators/pyneuroml:0.5.20","digest":"sha256:0592ac601916a4cddb9398823a539e209224c5919cca214a275296aa7a46d6b3"}}
        {"id":"brian2","name":"Brian 2","version":"2.5.0.3","image":{"url":"ghcr.io/biosimulators/brian2:2.5.0.3","digest":"sha256:1587b4dd3b5505ab25a965f8a81d902984854bbef13c6f1b8cf631af35b45cff"}}
        {"id":"cobrapy","name":"COBRApy","version":"0.23.0","image":{"url":"ghcr.io/biosimulators/cobrapy:0.23.0","digest":"sha256:477fa2018f3817b00432394b1bb291dcfdbde4d13f8cb69a68094bc2c4c2ab92"}}
        {"id":"cobrapy","name":"COBRApy","version":"0.24.0","image":{"url":"ghcr.io/biosimulators/cobrapy:0.24.0","digest":"sha256:9c4e5c5b429897a3af56b78e69ac1e28542428823d41750279cda5fe28a3080b"}}
        {"id":"masspy","name":"MASSpy","version":"0.1.6","image":{"url":"ghcr.io/biosimulators/masspy:0.1.6","digest":"sha256:eb21d48b8033e0de75c4674458b476d72ff3f82c7f1066d63417608fd430e100"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.38","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.38","digest":"sha256:e8dd40d48cdaf1b11208a7c3e669eca37fb031d5225b5b4d96eb267ae730dcfe"}}
        {"id":"bionetgen","name":"BioNetGen","version":"2.8.0","image":{"url":"ghcr.io/biosimulators/bionetgen:2.8.0","digest":"sha256:6b64ba14726b7f28921db5b96c8331c6bd9d0e2e541d4fe83fba2366a5593edb"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.67.3","image":{"url":"ghcr.io/biosimulators/smoldyn:2.67.3","digest":"sha256:5d4939cf99097ebbe972eef327ee86a43e2dc20a629e756347c660fd3e71f0b6"}}
        {"id":"copasi","name":"COPASI","version":"4.35.258","image":{"url":"ghcr.io/biosimulators/copasi:4.35.258","digest":"sha256:f4aeff7c2057e26840231f1969a1eda8ee2ba93e7470989b1d295d4e45158311"}}
        {"id":"copasi","name":"COPASI","version":"4.36.260","image":{"url":"ghcr.io/biosimulators/copasi:4.36.260","digest":"sha256:00e1b6c5414d3f4d7c2646c6da11ddf2cb402905217f7181e0be487a3fe62222"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.48","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.48","digest":"sha256:03f0e622174dfaf313a40e45be7c839aecfca252b4ddefc66dff49838b2ec23e"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.4.0.68","image":{"url":"ghcr.io/biosimulators/vcell:7.4.0.68","digest":"sha256:190a1eed6736057a167ff60ea3698731b157626176b7a9e9e5784c9d032c35d7"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.69","image":{"url":"ghcr.io/biosimulators/smoldyn:2.69","digest":"sha256:992788cd8b5c6f7d6cf3a5c6a39f4f3b9426075074b76306004ac997cb15fe75"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.70","image":{"url":"ghcr.io/biosimulators/smoldyn:2.70","digest":"sha256:af970afed751bcd79401d9640a81e381fb16cd8cac8388daec0719b6130862c0"}}
        {"id":"tellurium","name":"tellurium","version":"2.2.8","image":{"url":"ghcr.io/biosimulators/tellurium:2.2.8","digest":"sha256:8142fc0f07418f77a27785f1797f4c74e72ca6554b613360d3c62236e728d931"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.28","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.28","digest":"sha256:18e6ac855aa6b5bfe70cc245b10300e815ddcefefb4f57cdd149d7be5b15ec71"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.30","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.30","digest":"sha256:10caecb4952a830c8306700dd0d9b7c21a99f51010edc47624ad722811c86741"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.34","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.34","digest":"sha256:576883cf2685297400b7f976985f03dc8d1fbf8b46525a2fbef8e41e10b6021e"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.36","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.36","digest":"sha256:096446479e4ae135b9147104b540a9a6d6223279c98661c42f43081ac5fba21d"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.37","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.37","digest":"sha256:47979e5c16f910fcc0cc08f6ef57d109d89245573d31ef4b41ad52bb924bb72c"}}
        {"id":"amici","name":"AMICI","version":"0.18.1","image":{"url":"ghcr.io/biosimulators/amici:0.18.1","digest":"sha256:cf17b7a576bdb9ef0134590e7da3e757d11765086b8f51ea3ee84cd088fa171d"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.45","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.45","digest":"sha256:78ae012e68a32c2d0cb9548079eb5e62b88ab74f0b349cb5fab7580712f7a9e6"}}
        {"id":"smoldyn","name":"Smoldyn","version":"2.72","image":{"url":"ghcr.io/ssandrews/smoldyn/biosimulators_smoldyn:2.72","digest":"sha256:8aa0cd3eb3b0219dda000f243b4745dc3965fe5f1c082a2dfb611b7ae77edbc6"}}
        {"id":"copasi","name":"COPASI","version":"4.41.280","image":{"url":"ghcr.io/biosimulators/copasi:4.41.280","digest":"sha256:af7951180e324ca7e35060be8e55ac70712c5e7d0036df10a5802d7d1fad5347"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.80","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.80","digest":"sha256:0554056282005ed410a5e3e2ed86c72c2ead8bcd571210964bf2a6c14645c199"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.86-dev1","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.86-dev1","digest":"sha256:fab48bdd2c620acaf334f8e60ab87858f2816ea87b6160d48f510a43dc152a43"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.89","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.89","digest":"sha256:9c47976b6358c6083d33269c5fd8ea67f2cd507333177b9d4b7f49843dae56eb"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.99","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.99","digest":"sha256:84c1cf7409ef07ea53a220e85cff6b182694b6f781d8f3502a908486d406b97e"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.108","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.108","digest":"sha256:2ebcd968564459002769e567cd451f5c41e76add179bae27a9a43497e138ff00"}}
        {"id":"copasi","name":"COPASI","version":"4.42.284","image":{"url":"ghcr.io/biosimulators/copasi:4.42.284","digest":"sha256:915c10cdfe3066ff754f2a67727b73b825c5195ae6258e578a8f41556685d909"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.121","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.121","digest":"sha256:1a369286e15a6146f249acc029027991e0619cc18c8e452d0fc96f2e534604ca"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.5.0.127","image":{"url":"ghcr.io/biosimulators/vcell:7.5.0.127","digest":"sha256:0089380af4a4a54f7c30b5ca25dc81aa3e3130f41bb137de236cf35cbca32538"}}
        {"id":"pysces","name":"PySCeS","version":"1.2.1","image":{"url":"ghcr.io/biosimulators/pysces:1.2.1","digest":"sha256:a9f364bd9e00c0bbfae9fa3c8adb6a63a593a5cc4d980df225399c5eb8bbe7e1"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.6.0.40","image":{"url":"ghcr.io/biosimulators/vcell:7.6.0.40","digest":"sha256:530a2009fdd549ef1e23c0475358d8b245b3fe45ad4d07f0be89d13536cd6397"}}
        {"id":"pysces","name":"PySCeS","version":"1.2.2","image":{"url":"ghcr.io/biosimulators/pysces:1.2.2","digest":"sha256:0bba7f884629bf1b2ab6cb81ccd4d57a1512c09c196fe3cc4bb6a15f7edaf37f"}}
        {"id":"copasi","name":"COPASI","version":"4.44.295","image":{"url":"ghcr.io/biosimulators/copasi:4.44.295","digest":"sha256:6a0b2b782e983ad9de38767696c769d43e411d96d1070289c66838eecbfbfdfd"}}
        {"id":"tellurium","name":"tellurium","version":"2.2.10","image":{"url":"ghcr.io/biosimulators/tellurium:2.2.10","digest":"sha256:0c22827b4682273810d48ea606ef50c7163e5f5289740951c00c64c669409eae"}}
        {"id":"masspy","name":"MASSpy","version":"0.1.7","image":{"url":"ghcr.io/biosimulators/masspy:0.1.7","digest":"sha256:13a7ce784cf0561150d1e0623c47de84496068f59444589123d9ea845b7aaeae"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.7.0.7","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.7","digest":"sha256:50d06ccff8be3c5496a29ee3a3ce9b168d81955ceacce1808b4a3ae7b3ddb1c5"}}
        {"id":"copasi","name":"COPASI","version":"4.45.296","image":{"url":"ghcr.io/biosimulators/copasi:4.45.296","digest":"sha256:7c9cd076eeec494a653353777e42561a2ec9be1bfcc647d0ea84d89fe18999df"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.7.0.9","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.9","digest":"sha256:cfe9c9110a4d69ffc713afc2d51cb81c6f31a44950304fd8818a5678d67d2791"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.7.0.10","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.10","digest":"sha256:02494e4d849cf0681ee546b029e8f548694ca0cef1bb70127a69bf951183cb3a"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.7.0.12","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.12","digest":"sha256:6ab82cfc60518c5810d61dd47ad1e9acbfd539cb7d0f177e9e122997a30c6035"}}
        {"id":"vcell","name":"Virtual Cell","version":"7.7.0.13","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.13","digest":"sha256:828b2dc2b983de901c2d68eeb415cb22b46f1db04cdb9e8815d80bf451005216"}}
        """
        sim_versions = []
        for line in sim_versions_ndjson.strip().split("\n"):
            sim_versions.append(BiosimulatorVersion.model_validate_json(line.strip()))
        return sim_versions

    @override
    async def close(self) -> None:
        pass
