import { ApolloClient, InMemoryCache, HttpLink, gql, split } from "@apollo/client/core";
import { getMainDefinition } from "@apollo/client/utilities";
import { GraphQLWsLink } from "@apollo/client/link/subscriptions";
import { createClient } from "graphql-ws";

export { gql };

let _client: ApolloClient | null = null;

/**
 * Return the shared Apollo Client singleton.
 *
 * Uses a split link: WebSocket for subscriptions, HTTP for queries/mutations.
 * Session headers are injected by the patched global ``fetch()`` in app-shell;
 * the WS connection passes the session token via connectionParams.
 */
export function getClient(apiBase: string = "/api"): ApolloClient {
  if (_client) return _client;

  const httpLink = new HttpLink({ uri: `${apiBase}/graphql` });

  // WebSocket link for subscriptions (graphql-transport-ws protocol).
  // Only created when WebSocket is available (browser). In Node test
  // environments (happy-dom/vitest) WebSocket may not exist -- fall
  // back to HTTP-only so tests don't crash on import.
  let link = httpLink as ReturnType<typeof split>;
  if (typeof WebSocket !== "undefined" && typeof location !== "undefined") {
    const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
    const wsLink = new GraphQLWsLink(
      createClient({
        url: `${wsProtocol}//${location.host}${apiBase}/graphql`,
        connectionParams: () => {
          const token = localStorage.getItem("shenas-session");
          return token ? { authorization: token } : {};
        },
        retryAttempts: Infinity,
        shouldRetry: () => true,
      }),
    );
    link = split(
      ({ query }) => {
        const def = getMainDefinition(query);
        return def.kind === "OperationDefinition" && def.operation === "subscription";
      },
      wsLink,
      httpLink,
    );
  }

  _client = new ApolloClient({
    link,
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
