import { ApolloClient, InMemoryCache, HttpLink, gql } from "@apollo/client/core";

export { gql };

let _client: ApolloClient | null = null;

/**
 * Return the shared Apollo Client singleton.
 *
 * The first call creates the client; subsequent calls return the same instance.
 * Session headers are injected by the patched global ``fetch()`` in app-shell,
 * so no custom link middleware is needed here.
 */
export function getClient(apiBase: string = "/api"): ApolloClient {
  if (_client) return _client;
  _client = new ApolloClient({
    link: new HttpLink({ uri: `${apiBase}/graphql` }),
    cache: new InMemoryCache({
      typePolicies: {
        PluginInfoType: { keyFields: ["kind", "name"] },
        GqlEntityType: { keyFields: ["uuid"] },
        EntityTypeType: { keyFields: ["name"] },
        EntityRelationshipTypeType: { keyFields: ["name"] },
        TransformType: { keyFields: ["id"] },
        DataResourceType: { keyFields: ["id"] },
        PropertyType: { keyFields: ["id"] },
        CategorySetType: { keyFields: ["id"] },
        StatementType: { keyFields: ["entityId", "propertyId", "value"] },
      },
    }),
    defaultOptions: {
      watchQuery: { fetchPolicy: "cache-and-network" },
      query: { fetchPolicy: "cache-first" },
    },
  });
  return _client;
}
