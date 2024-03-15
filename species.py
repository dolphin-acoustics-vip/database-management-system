class SpeciesEncounterDTO:
    def __init__(self, species_id, species_name, genus_name, common_name, encounter_id, encounter_name, location, origin, notes):
        self.species_id = species_id
        self.species_name = species_name
        self.genus_name = genus_name
        self.common_name = common_name
        self.encounter_id = encounter_id
        self.encounter_name = encounter_name
        self.location = location
        self.origin = origin
        self.notes = notes

class Species:
    def __init__(self, id, species_name, genus_name, common_name):
        self.id = id
        self.species_name = species_name
        self.genus_name = genus_name
        self.common_name = common_name
    
    @property
    def id(self):
        return self._id if self._id is not None else ''
    
    @property
    def species_name(self):
        return self._species_name
    
    @property
    def genus_name(self):
        return self._genus_name if self._genus_name is not None else ''
    
    @property
    def common_name(self):
        return self._common_name if self._common_name is not None else ''