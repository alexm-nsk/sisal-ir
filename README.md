Experimental Cloud Sisal parser. It will translate code like:

function Fib( M : integer returns integer )
  if M < 2 then
    M
  else
    Fib( M - 1 ) + Fib (M-2,2)
  end if
end function

into an IR like:

{
  "name": {
    "name": "Fib",
    "type": "identifier"
  },
  "node_id": "node8",
  "nodes": [
    {
      "Cond": {
        "name": "binary",
        "node_id": "node1",
        "nodes": [
          {
            "name": "M",
            "type": "identifier"
          },
          {
            "type": "literal",
            "value": 2
          }
        ],
        "op": "<",
        "type": "binary"
      },
      "Else": {
        "name": "binary",
        "node_id": "node6",
        "nodes": [
          {
            "name": "call",
            "node_id": "node3",
            "nodes": [
              {
                "name": "binary",
                "node_id": "node2",
                "nodes": [
                  {
                    "name": "M",
                    "type": "identifier"
                  },
                  {
                    "type": "literal",
                    "value": 1
                  }
                ],
                "op": "-",
                "type": "binary"
              }
            ],
            "type": "call"
          },
          {
            "name": "call",
            "node_id": "node5",
            "nodes": [
              {
                "name": "binary",
                "node_id": "node4",
                "nodes": [
                  {
                    "name": "M",
                    "type": "identifier"
                  },
                  {
                    "type": "literal",
                    "value": 2
                  }
                ],
                "op": "-",
                "type": "binary"
              }
            ],
            "type": "call"
          }
        ],
        "op": "+",
        "type": "binary"
      },
      "Then": {
        "name": "M",
        "type": "identifier"
      },
      "name": "if",
      "node_id": "node7",
      "type": "if_else"
    }
  ],
  "type": "function"
}
