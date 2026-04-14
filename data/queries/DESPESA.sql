-- DESPESA.sql — Despesa Orçamentária (Balanço Orçamentário)
-- Placeholder {SCHEMA_ANO} será substituído pelo Python com o ano corrente (ex: mil2026)
-- O schema mil2001 é fixo (saldocontabil_ex)
-- Não colocar ponto-e-vírgula no final
-- Contas: empenhada 622130000-622139999, liquidada 622130300/400/700, paga 622920104
--
-- IMPORTANTE: JOINs com classificacaoorcamentaria usam subquery com
-- GROUP BY para garantir 1 linha por código, evitando duplicação
-- (produto cartesiano nas UGs 900101 e 320203).

SELECT
    v.coexercicio,
    v.inmes,
    v.coug,
    v.noug,
    v.cocontacontabil,
    v.vadebito,
    v.vacredito,
    CASE
        WHEN v.cocontacontabil LIKE '5%' THEN (v.vadebito - v.vacredito)
        WHEN v.cocontacontabil LIKE '6%' THEN (v.vacredito - v.vadebito)
        ELSE 0
    END AS SALDO,

    -- Classificação da despesa (conatureza)
    v.conatureza || '00' AS DESPESA,
    c_desp.NOME AS NOME_DESPESA,

    SUBSTR(v.conatureza, 1, 1) || '0000000' AS CATEGORIA_ECONOMICA,
    c_cat_desp.NOME AS NOME_CATEGORIA_ECONOMICA,

    SUBSTR(v.conatureza, 1, 2) || '000000' AS GND,
    c_gnd.NOME AS NOME_GND,

    SUBSTR(v.conatureza, 3, 2) AS INTRA,

    -- Fonte de recurso
    TO_CHAR(v.cofonte) AS FONTE,
    SUBSTR(TO_CHAR(v.cofonte), 1, 4) AS FONTE_AGRUPADA,
    fr.COFONTEFEDERAL,
    fr_nome.NOFONTE AS NOME_FONTE,

    -- Subelemento (8 dígitos: posições 33 a 40 da conta corrente)
    SUBSTR(v.cocontacorrente, 33, 8) AS SUBELEMENTO,
    c_sub.NOME AS NOME_SUBELEMENTO,

    -- Função e subfunção
    v.cofuncao,
    f.NOFUNCAO,
    v.cosubfuncao,
    sf.NOSUBFUNCAO

FROM mil2001.saldocontabil_ex v

-- Subqueries com GROUP BY garantem 1 linha por código
LEFT JOIN (SELECT TO_CHAR(COCLASSEORC) AS COD, MIN(NOCLASSIFICACAO) AS NOME
             FROM {SCHEMA_ANO}.classificacaoorcamentaria GROUP BY TO_CHAR(COCLASSEORC)) c_desp
       ON c_desp.COD = v.conatureza || '00'

LEFT JOIN (SELECT TO_CHAR(COCLASSEORC) AS COD, MIN(NOCLASSIFICACAO) AS NOME
             FROM {SCHEMA_ANO}.classificacaoorcamentaria GROUP BY TO_CHAR(COCLASSEORC)) c_cat_desp
       ON c_cat_desp.COD = SUBSTR(v.conatureza, 1, 1) || '0000000'

LEFT JOIN (SELECT TO_CHAR(COCLASSEORC) AS COD, MIN(NOCLASSIFICACAO) AS NOME
             FROM {SCHEMA_ANO}.classificacaoorcamentaria GROUP BY TO_CHAR(COCLASSEORC)) c_gnd
       ON c_gnd.COD = SUBSTR(v.conatureza, 1, 2) || '000000'

LEFT JOIN (SELECT TO_CHAR(COCLASSEORC) AS COD, MIN(NOCLASSIFICACAO) AS NOME
             FROM {SCHEMA_ANO}.classificacaoorcamentaria GROUP BY TO_CHAR(COCLASSEORC)) c_sub
       ON c_sub.COD = SUBSTR(v.cocontacorrente, 33, 8)

-- Fonte: JOIN direto (cofonte é chave única)
LEFT JOIN {SCHEMA_ANO}.fonterecurso fr
       ON TO_CHAR(v.cofonte) = TO_CHAR(fr.COFONTE)

-- Fonte agrupada (4 dígitos + '00000')
LEFT JOIN {SCHEMA_ANO}.fonterecurso fr_nome
       ON SUBSTR(TO_CHAR(v.cofonte), 1, 4) || '00000' = TO_CHAR(fr_nome.COFONTE)

-- Função (cofuncao é chave única)
LEFT JOIN {SCHEMA_ANO}.funcao f
       ON TO_CHAR(v.cofuncao) = TO_CHAR(f.COFUNCAO)

-- Subfunção (cosubfuncao é chave única)
LEFT JOIN {SCHEMA_ANO}.subfuncao sf
       ON TO_CHAR(v.cosubfuncao) = TO_CHAR(sf.COSUBFUNCAO)

WHERE (
        -- Empenhada / Liquidada / Paga (classe 6)
        v.cocontacontabil BETWEEN '622130000' AND '622139999'
     OR v.cocontacontabil = '622920104'
        -- Despesa Autorizada (classe 5)
     OR v.cocontacontabil BETWEEN '522110000' AND '522129999'
     OR v.cocontacontabil BETWEEN '522150000' AND '522159999'
     OR v.cocontacontabil BETWEEN '522190000' AND '522199999'
      )
  AND v.coexercicio IN (
      TO_CHAR(EXTRACT(YEAR FROM SYSDATE)),
      TO_CHAR(EXTRACT(YEAR FROM SYSDATE) - 1)
  )
