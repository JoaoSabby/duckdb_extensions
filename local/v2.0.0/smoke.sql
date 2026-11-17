-- Valida o registro do Dash e o JSON produzido pelo parser TOML.
PRAGMA dash_home;
SELECT CASE WHEN parse_toml('key = 42')::VARCHAR = '{"key":42}'
            THEN 'toml OK' ELSE error('toml') END;

-- Usa operandos com larguras distintas e verifica arredondamento e média.
SELECT CASE WHEN decimal_div(10.00, 4.00) = 2.5
                 AND round_floor(2.52, 1) = 2.5 AND decimal_avg(x) = 1.5
            THEN 'decimal_arithmetic OK' ELSE error('decimal_arithmetic') END
FROM (VALUES (1.00), (2.00)) AS t(x);

-- O enum da extensão define as colunas produzidas pelo pivot.
CREATE TEMP TABLE mov AS
SELECT * FROM (VALUES ('A', 'Online', 10), ('A', 'Loja', 12), ('B', 'Online', 5)) AS t(loja, canal, valor);
CREATE TYPE columns_parameter_enum AS ENUM (SELECT DISTINCT canal FROM mov ORDER BY canal);
SELECT CASE WHEN count(*) = 2 AND sum(Online) = 15
            THEN 'pivot_table OK' ELSE error('pivot_table') END
FROM pivot_table(['mov'], ['sum(valor)'], ['loja'], ['canal'], [], values_axis := 'columns');

-- O modo spec exercita o transporte Arrow e a renderização sem abrir navegador.
SET ggsql_output = 'spec';
SELECT CASE WHEN json_valid(ggsql('SELECT 1 AS x, 2 AS y VISUALISE x, y DRAW point'))
            THEN 'ggsql OK' ELSE error('ggsql') END;

-- A extensão deve registrar as opções e permitir o planejamento de um CTAS.
SET duck_lineage_namespace = 'duckdb-extension-test';
CREATE TEMP TABLE lineage_output AS SELECT loja, valor * 2 AS valor_dobrado FROM mov;
SELECT CASE WHEN sum(valor_dobrado) = 54 THEN 'duck_lineage OK' ELSE error('duck_lineage') END
FROM lineage_output;
