import { gqlTag as gql } from "shenas-frontends";

// --- Fragments ---
// Each fragment declares the fields a specific UI concern needs.
// Page-level queries compose fragments via ...spread.

/** Sidebar plugin card: minimal fields for the plugin list. */
export const PLUGIN_CARD_FRAGMENT = gql`
  fragment PluginCard on PluginInfoType {
    name
    displayName
    enabled
    syncedAt
    hasAuth
    isAuthenticated
    entityTypes
    entityUuids
    tables
    totalRows
  }
`;

/** Dashboard entry for the top nav bar. */
export const DASHBOARD_FRAGMENT = gql`
  fragment DashboardEntry on DashboardType {
    name
    displayName
    tag
    js
    description
  }
`;

// --- Shell data (blocking: app can't render without this) ---
export const GET_SHELL_DATA = gql`
  ${DASHBOARD_FRAGMENT}
  {
    pluginKinds
    dashboards {
      ...DashboardEntry
    }
    themeData: theme {
      css
    }
    deviceName
    workspace
    hotkeys
  }
`;

// --- Sidebar plugin lists (non-blocking: sidebar populates after shell renders) ---
export const GET_SIDEBAR_PLUGINS = gql`
  ${PLUGIN_CARD_FRAGMENT}
  {
    source: plugins(kind: "source") {
      ...PluginCard
    }
    dataset: plugins(kind: "dataset") {
      ...PluginCard
    }
    dashboard: plugins(kind: "dashboard") {
      ...PluginCard
    }
    frontend: plugins(kind: "frontend") {
      ...PluginCard
    }
    theme: plugins(kind: "theme") {
      ...PluginCard
    }
    model: plugins(kind: "model") {
      ...PluginCard
    }
    transformer: plugins(kind: "transformer") {
      ...PluginCard
    }
    analysis: plugins(kind: "analysis") {
      ...PluginCard
    }
  }
`;

// --- Focused single-purpose queries (lazy, avoid re-fetching the monolith) ---
export const GET_HOTKEYS = gql`
  {
    hotkeys
  }
`;

export const GET_WORKSPACE = gql`
  {
    workspace
  }
`;

export const GET_DASHBOARDS = gql`
  ${DASHBOARD_FRAGMENT}
  {
    dashboards {
      ...DashboardEntry
    }
  }
`;

function dynamicGql(query: string) {
  return gql(Object.assign([query], { raw: [query] }) as unknown as TemplateStringsArray);
}

export { dynamicGql };

// --- Catalog ---

/** Core data resource fields used by both list and detail views. */
export const DATA_RESOURCE_FRAGMENT = gql`
  fragment DataResourceFields on DataResourceType {
    id
    schemaName
    tableName
    displayName
    description
    plugin {
      name
      displayName
    }
    kind
    queryHint
    asOfMacro
    primaryKey
    columns {
      name
      dbType
      nullable
      description
      unit
    }
    timeColumns {
      timeAt
      timeStart
      timeEnd
    }
    freshness {
      lastRefreshed
      slaMinutes
      isStale
    }
    quality {
      expectedRowCountMin
      expectedRowCountMax
      actualRowCount
      latestChecks {
        checkType
        status
        message
        checkedAt
      }
    }
    userNotes
    tags
  }
`;

export const GET_DATA_RESOURCES = gql`
  ${DATA_RESOURCE_FRAGMENT}
  {
    dataResources {
      ...DataResourceFields
    }
  }
`;

export const GET_DATA_RESOURCE_DETAIL = gql`
  ${DATA_RESOURCE_FRAGMENT}
  query GetDataResourceDetail($id: String!) {
    dataResource(resourceId: $id) {
      ...DataResourceFields
      upstreamTransforms {
        id
        transformType
        source {
          id
          displayName
        }
        description
      }
      downstreamTransforms {
        id
        transformType
        target {
          id
          displayName
        }
        description
      }
    }
  }
`;

// --- Entities ---

export const ENTITY_FRAGMENT = gql`
  fragment EntityFields on GqlEntityType {
    uuid
    type
    name
    description
    status
    isMe
    sources
  }
`;

export const ENTITY_TYPE_FRAGMENT = gql`
  fragment EntityTypeFields on EntityTypeType {
    name
    displayName
    description
    icon
    parent
    isAbstract
  }
`;

export const ENTITY_REL_TYPE_FRAGMENT = gql`
  fragment EntityRelTypeFields on EntityRelationshipTypeType {
    name
    displayName
    inverseName
    isSymmetric
    domainTypes
    rangeTypes
  }
`;

export const GET_ENTITIES_DATA = gql`
  ${ENTITY_FRAGMENT}
  ${ENTITY_TYPE_FRAGMENT}
  ${ENTITY_REL_TYPE_FRAGMENT}
  {
    entities {
      ...EntityFields
    }
    entityRelationships {
      fromUuid
      toUuid
      type
      description
    }
    entityTypes {
      ...EntityTypeFields
    }
    entityRelationshipTypes {
      ...EntityRelTypeFields
    }
  }
`;

// --- Hypotheses ---
export const GET_HYPOTHESES = gql`
  {
    hypotheses {
      id
      question
      plan
      inputs
      interpretation
      model
      mode
      promotedTo
      createdAt
      recipeJson
      resultJson
    }
  }
`;

export const GET_ANALYSIS_MODES = gql`
  {
    analysisModes
  }
`;

// --- Transforms ---

export const DATA_RESOURCE_REF_FRAGMENT = gql`
  fragment DataResourceRef on DataResourceRefType {
    id
    schemaName
    tableName
    displayName
  }
`;

export const TRANSFORM_FRAGMENT = gql`
  ${DATA_RESOURCE_REF_FRAGMENT}
  fragment TransformFields on TransformType {
    id
    transformType
    source {
      ...DataResourceRef
    }
    target {
      ...DataResourceRef
    }
    sourcePlugin
    params
    description
    isDefault
    enabled
    sql
  }
`;

export const GET_TRANSFORMS = gql`
  ${TRANSFORM_FRAGMENT}
  query GetTransforms($source: String) {
    transforms(source: $source) {
      ...TransformFields
    }
    dependencies {
      source
      targets
    }
    transformTypes {
      name
      displayName
      description
      paramSchema {
        name
        label
        type
        required
        description
        default
        options
      }
    }
  }
`;

export const GET_TABLE_COLUMNS = gql`
  query GetTableColumns($s: String!, $t: String!) {
    tableColumns(schema: $s, table: $t)
  }
`;

// --- Plugin Detail ---
// Note: pluginInfo query is dynamic (built per kind), keep as string builder
export const GET_THEME = gql`
  {
    theme {
      css
    }
  }
`;

export const GET_SUGGESTED_DATASETS = gql`
  query GetSuggestedDatasets($source: String) {
    suggestedDatasets(source: $source) {
      name
      title
      grain
      tableName
    }
  }
`;

// --- Categories ---
export const GET_CATEGORY_SETS = gql`
  {
    categorySets {
      id
      displayName
      description
      values {
        value
        sortOrder
        color
      }
    }
  }
`;

// --- Config ---
export const GET_PLUGIN_CONFIG = gql`
  query GetPluginConfig($kind: String!, $name: String!) {
    pluginConfig(kind: $kind, name: $name) {
      key
      label
      value
      description
      uiWidget
    }
  }
`;

// --- Auth ---
export const GET_AUTH_FIELDS = gql`
  query GetAuthFields($source: String!) {
    authFields(source: $source) {
      fields {
        name
        prompt
        hide
      }
      instructions
      stored
    }
  }
`;

// --- Available Plugins ---
export const GET_AVAILABLE_PLUGINS = gql`
  query GetAvailablePlugins($kind: String!) {
    availablePlugins(kind: $kind)
  }
`;

// --- Flow ---
export const GET_SOURCE_ENTITIES = gql`
  query GetSourceEntities($plugin: String!) {
    sourceEntitiesForPlugin(plugin: $plugin) {
      uuid
      type
      name
      description
      status
    }
    entityTypes {
      name
      displayName
      isAbstract
      parent
    }
  }
`;

export const GET_ENTITY_WITH_STATEMENTS = gql`
  query GetEntityWithStatements($uuid: String!) {
    entity(uuid: $uuid) {
      uuid
      type
      name
      description
      status
      statements {
        entityId
        propertyId
        value
        valueLabel
        rank
        qualifiers
        source
        propertyLabel
        datatype
      }
    }
  }
`;
