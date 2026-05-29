import {
  type GraphQLNamedType,
  type GraphQLSchema,
  isEnumType,
  isInputObjectType,
  isInterfaceType,
  isIntrospectionType,
  isObjectType,
  isScalarType,
  isUnionType,
} from "graphql";
import { useState } from "react";

interface Props {
  schema: GraphQLSchema | null;
  onFetch: () => void;
  fetching: boolean;
  fetchError: string | null;
}

function typeKindLabel(type: GraphQLNamedType): string {
  if (isObjectType(type)) return "object";
  if (isScalarType(type)) return "scalar";
  if (isInputObjectType(type)) return "input";
  if (isEnumType(type)) return "enum";
  if (isInterfaceType(type)) return "interface";
  if (isUnionType(type)) return "union";
  return "";
}

function typeFields(
  type: GraphQLNamedType,
): { name: string; typeStr: string }[] {
  if (isObjectType(type) || isInterfaceType(type) || isInputObjectType(type)) {
    return Object.values(type.getFields()).map((f) => ({
      name: f.name,
      typeStr: f.type.toString(),
    }));
  }
  return [];
}

function TypeRow({
  type,
  defaultExpanded,
}: {
  type: GraphQLNamedType;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const fields = typeFields(type);
  const hasFields = fields.length > 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => hasFields && setExpanded((e) => !e)}
        className={`flex w-full items-center gap-1 px-2 py-0.5 text-left text-xs ${
          hasFields ? "cursor-pointer hover:bg-muted" : "cursor-default"
        }`}
      >
        <span className="w-3 text-purple-500 dark:text-purple-400">
          {hasFields ? (expanded ? "▼" : "▶") : ""}
        </span>
        <span className="font-medium text-purple-700 dark:text-purple-300">
          {type.name}
        </span>
        <span className="ml-1 text-[10px] text-muted-foreground">
          {typeKindLabel(type)}
        </span>
      </button>
      {expanded && hasFields && (
        <div className="py-0.5 pl-6">
          {fields.map((f) => (
            <div key={f.name} className="py-0.5 text-xs">
              <span className="text-blue-600 dark:text-blue-400">{f.name}</span>
              <span className="text-muted-foreground"> {f.typeStr}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const _BUILTIN_SCALAR_NAMES = new Set([
  "Boolean",
  "Float",
  "ID",
  "Int",
  "String",
]);

function FetchButton({
  fetching,
  onFetch,
}: {
  fetching: boolean;
  onFetch: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onFetch}
      disabled={fetching}
      className="rounded bg-muted px-2 py-0.5 text-xs text-foreground hover:bg-muted/80 disabled:opacity-50"
    >
      {fetching ? "Fetching…" : "Fetch Schema"}
    </button>
  );
}

export function SchemaExplorer({
  schema,
  onFetch,
  fetching,
  fetchError,
}: Props) {
  if (!schema) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <p className="text-sm">No schema loaded</p>
        <FetchButton fetching={fetching} onFetch={onFetch} />
        {fetchError && (
          <p className="text-xs text-red-600 dark:text-red-400">{fetchError}</p>
        )}
      </div>
    );
  }

  const typeMap = schema.getTypeMap();
  const queryType = schema.getQueryType();
  const mutationType = schema.getMutationType();
  const subscriptionType = schema.getSubscriptionType();
  const rootNames = new Set(
    [queryType?.name, mutationType?.name, subscriptionType?.name].filter(
      (n): n is string => n != null,
    ),
  );
  const rootTypes = [queryType, mutationType, subscriptionType].filter(
    (t): t is NonNullable<typeof t> => t != null,
  );

  const objectTypes = Object.values(typeMap).filter(
    (t) => isObjectType(t) && !rootNames.has(t.name) && !isIntrospectionType(t),
  );
  const otherTypes = Object.values(typeMap).filter(
    (t) =>
      !isObjectType(t) &&
      !isIntrospectionType(t) &&
      !_BUILTIN_SCALAR_NAMES.has(t.name),
  );
  const builtinTypes = Object.values(typeMap).filter(
    (t) => isIntrospectionType(t) || _BUILTIN_SCALAR_NAMES.has(t.name),
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-2 py-1">
        <span className="text-xs text-muted-foreground">Schema</span>
        <div className="flex items-center gap-2">
          {fetchError && (
            <span className="text-xs text-red-600 dark:text-red-400">
              {fetchError}
            </span>
          )}
          <FetchButton fetching={fetching} onFetch={onFetch} />
        </div>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {rootTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Root Types
            </div>
            {rootTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded />
            ))}
          </>
        )}
        {objectTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Object Types
            </div>
            {objectTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded />
            ))}
          </>
        )}
        {otherTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Other Types
            </div>
            {otherTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded={false} />
            ))}
          </>
        )}
        {builtinTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Built-in
            </div>
            {builtinTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded={false} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
