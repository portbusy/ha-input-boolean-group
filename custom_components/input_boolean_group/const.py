"""Constants for the Input Boolean Group integration."""

DOMAIN = "input_boolean_group"

# Legacy config key (kept for backward compatibility)
CONF_ALL_MODE = "all_mode"

# Current config keys
CONF_ENTITIES = "entities"
CONF_MODE = "mode"
CONF_ENTITIES_ON = "entities_on"
CONF_ENTITIES_OFF = "entities_off"
CONF_CONDITIONS = "conditions"

# Mode values
MODE_ANY = "any"
MODE_ALL = "all"
MODE_UNION = "union"
MODE_CONDITIONS = "conditions"

# State attributes
ATTR_ENTITY_IDS = "entity_id"
ATTR_ALL_MODE = "all_mode"
ATTR_MODE = "mode"
ATTR_ENTITIES_ON = "entities_on"
ATTR_ENTITIES_OFF = "entities_off"
