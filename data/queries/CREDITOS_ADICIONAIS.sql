SELECT
    coexercicio,
    inmes,
    coug,
    noug,
    cocontacontabil,
    cocontacorrente,
    inesfera,
    couo,
    cofuncao,
    cosubfuncao,
    coprograma,
    coprojeto,
    cosubtitulo,
    cofonte,
    conatureza,
    incategoria,
    (vadebito - vacredito) AS saldo
FROM
    mil2001.saldocontabil_ex
WHERE
    (cocontacontabil IN (522120100, 522120201, 522120202, 522120301,
                         522150100, 522150200, 522150300,
                         522130100, 522130101, 522130102, 522130199))
