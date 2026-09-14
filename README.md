# ringr_agents

Arquitectura de agentes conversacionales para procesar turnos de forma estructurada, extensible y testeable.

El proyecto simula dos casos de uso:

- `DebtAgent`: registra compromisos de pago.
- `AssistanceAgent`: registra solicitudes para atención humana.

Las integraciones HTTP no realizan llamadas de red. Construyen la request completa y simulan una respuesta del endpoint.

## Arquitectura

```text
ConversationModel
        |
        v
answer_user() -> texto del usuario
        |
        v
ParserModel
        |
        v
parse_data() -> datos estructurados
        |
        v
BaseAgent.handle_turn()
        |
        +--> validación y normalización
        |
        +--> decisión de acción
        |
        +--> idempotencia
        |
        +--> build_request()
        |
        +--> execute() simulado
        |
        v
AgentResult + respuesta al usuario
```

## Estructura

```text
agents/
  base.py                 Ciclo común de vida del agente.
  debt_agent.py           Reglas del agente de cobros.
  assistance_agent.py     Reglas del agente de atención.

models/
  models.py               Modelos simulados y Protocols de entrada.

integrations/
  contracts.py            Contrato único para acciones externas.
  action.py               Acción HTTP simulada y fábricas de acciones.

utils/
  validators.py           Validación y normalización de datos.
  idempotency.py          Identificadores y almacenamiento de acciones.

errors.py                 Errores y códigos de estado del agente.
tests/                    Tests unitarios y de ciclo completo.
```

## Ciclo de un turno

Cada turno se procesa mediante:

```python
result = agent.handle_turn(conversation, parser)
```

El ciclo realiza estos pasos:

1. Ejecuta `ConversationModel.answer_user()`.
2. Ejecuta `ParserModel.parse_data(user_text)`.
3. Comprueba y normaliza los datos.
4. Decide si existe una acción externa.
5. Calcula un identificador idempotente.
6. Ignora acciones ya procesadas.
7. Construye la request.
8. Ejecuta la acción de forma simulada.
9. Interpreta el código HTTP simulado.
10. Genera una respuesta conversacional en `AgentResult.agent_response`.
11. Registra el ciclo mediante `logging`.

Los Protocols permiten usar implementaciones reales o mocks sin acoplar el agente a un proveedor concreto de LLM.

## Modelos simulados

```python
from models import ConversationModel, ParserModel

conversation = ConversationModel("Confirmo el pago")
parser = ParserModel(
    {
        "commitment_date": "2026-09-15",
        "committed_amount": 150.0,
    }
)
```

`ConversationModel` devuelve el texto configurado. `ParserModel` devuelve un diccionario preconfigurado. No se realizan llamadas a LLM.

## Agentes

### DebtAgent

Datos esperados:

```python
{
    "commitment_date": "2026-09-15",
    "committed_amount": 150.0,
    "extra_headers": {"X-Trace": "example"},
}
```

Cuando fecha y cantidad son válidas, construye:

```text
POST https://api.ringr.debt/v1/commitment
```

Body:

```json
{
  "commitment_date": "2026-09-15",
  "committed_amount": 150.0
}
```

Si solo se proporciona uno de los dos campos, el turno termina con `validation_error`. Si ambos son `None`, termina con `no_action`.

### AssistanceAgent

Datos esperados:

```python
{
    "request": "Necesito ayuda con mi factura",
    "extra_headers": {"X-Queue": "human"},
}
```

Cuando existe una solicitud válida, construye:

```text
POST https://api.ringr.assistance/v1/request
```

Body:

```json
{
  "request": "Necesito ayuda con mi factura"
}
```

Una solicitud vacía o `None` termina con `no_action`.

## Requests HTTP simuladas

Todas las requests incluyen:

```text
Authorization: Bearer <RINGR_BEARER_TOKEN>
Content-Type: application/json
```

Los headers adicionales del parser se conservan y se normalizan a minúsculas. `authorization` y `content-type` no pueden ser sobrescritos por defecto.

`HttpAction.execute()` no usa red. Devuelve un `HttpResponse` con el código configurado:

```python
HttpAction(..., simulated_status_code=200)
```

Un código `200` o cualquier código menor que `400` genera `action_succeeded`. Un código `400` o superior genera `action_failed` y no registra la acción como procesada, por lo que puede reintentarse.

## Resultado del turno

`handle_turn` devuelve `AgentResult`:

```python
AgentResult(
    action_request=request,
    status="action_succeeded",
    details={"action_id": "..."},
    response_status_code=200,
    agent_response="He registrado tu compromiso de pago correctamente.",
)
```

Estados disponibles:

- `action_succeeded`: acción procesada correctamente.
- `no_action`: no se cumplen las condiciones para actuar.
- `duplicate_ignored`: la acción ya fue procesada.
- `conversation_error`: no se pudo obtener la respuesta del usuario.
- `parser_error`: el parser falló o no devolvió un diccionario.
- `validation_error`: los datos no son válidos.
- `action_id_error`: no se pudo calcular el identificador.
- `build_request_error`: no se pudo construir o ejecutar la acción.
- `action_failed`: el endpoint simulado devolvió un error HTTP.

## Idempotencia

El identificador de idempotencia se calcula a partir de la URL y el body de la acción. El JSON se serializa de forma determinista antes de calcular SHA-256, por lo que acciones con el mismo contenido producen el mismo identificador aunque difiera el orden de las claves.

`IdempotencyStore` es un almacenamiento en memoria sustituible. Para producción puede reemplazarse por una base de datos sin cambiar el flujo de `BaseAgent`.

## Extensibilidad

Para añadir un nuevo tipo de acción:

1. Implementa `Action` en `integrations/contracts.py`.
2. Implementa `id`, `build_request` y `execute`.
3. Crea una fábrica de acción en `integrations`.
4. Añade un agente que herede de `BaseAgent`.
5. Implementa `_validate_and_normalize` y `_decide_action`.
6. Añade tests para éxito, ausencia de acción, errores e idempotencia.

`BaseAgent` no necesita conocer los detalles de la nueva integración.

## Procesamiento asíncrono y evoluciòn futura.

El núcleo actual (`BaseAgent.handle_turn`) es síncrono de forma intencionada: procesa un turno completo y devuelve su resultado antes de finalizar el flujo de ejecución.

Esta decisión mantiene el procesamiento determinista y evita introducir complejidad de concurrencia que no es necesaria para los requisitos actuales.

En un escenario de alto volumen, una capa externa de workers podría ejecutar varios turnos en paralelo. En ese caso, el almacenamiento de idempotencia debería ser persistente y la operación de registro debería ser atómica para evitar que dos workers procesen simultáneamente la misma acción.

La arquitectura actual permite añadir esta capa de orquestación sin modificar la lógica de negocio de los agentes.

## Logging

El ciclo utiliza el módulo estándar `logging` para registrar:

- inicio del turno;
- errores de conversación, parser y validación;
- ausencia de acción;
- duplicados;
- éxito o fallo de la acción.

Los logs no incluyen el token Bearer ni la request completa.

Para configurar logs desde una aplicación:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

## Tests

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Para ejecutar un archivo concreto:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_turn_models_and_requests.py -q
```

Para medir cobertura:

```powershell
.\.venv\Scripts\python.exe -m coverage run -m pytest -q
.\.venv\Scripts\python.exe -m coverage report -m
```

Estado validado actualmente:

```text
39 passed
Cobertura aproximada: 98%
```

## Decisiones de diseño

- `BaseAgent` concentra el ciclo común del turno:
  obtención del mensaje, parsing, validación, decisión, idempotencia,
  ejecución y respuesta al usuario. Esto evita duplicar el flujo en cada
  agente y facilita añadir nuevos casos de uso.

- Cada agente mantiene únicamente sus reglas de negocio. `DebtAgent`
  conoce los requisitos de fecha y cantidad, mientras que
  `AssistanceAgent` conoce los requisitos de una solicitud de atención.
  De esta forma, las reglas de un agente no contaminan a los demás.

- `Action` tiene una única definición compartida en
  `integrations/contracts.py`. Esta abstracción permite añadir nuevas
  acciones, como email, SMS o base de datos, sin modificar `BaseAgent`.

- Los modelos se expresan mediante `Protocol`. Esto permite utilizar
  implementaciones reales, simulaciones o mocks siempre que cumplan los
  métodos `answer_user()` y `parse_data()`. Así se reduce el acoplamiento
  con proveedores concretos de LLM.

- La autenticación se añade en la capa de integración, no en los agentes.
  Así, los agentes solo crean acciones de negocio y no conocen los detalles
  técnicos de HTTP.

- La idempotencia se aplica antes de ejecutar una acción repetida. El
  identificador se calcula de forma determinista a partir de la URL y el
  body. La acción solo se registra como procesada después de una respuesta
  exitosa.

- Las acciones fallidas no se registran como procesadas. Esto permite
  reintentar una operación cuando el endpoint simulado devuelve un error.

- La respuesta conversacional se separa del resultado técnico. El agente 
  devuelve tanto el estado de la operación como agent_response, que representa el mensaje 
  que recibiría el usuario. En una puesta en producción, esta capa podría generar respuestas 
  dinámicas basadas en el contexto de la conversación y el resultado de la acción.

- El logging se realiza en `BaseAgent`, porque allí se conocen todas las
  etapas del ciclo. Los logs permiten observar éxitos, errores y duplicados
  sin incluir tokens ni requests completas.

- No se introduce concurrencia ni procesamiento distribuido porque no forma
  parte de los requisitos actuales. La implementación actual es síncrona,
  determinista y adecuada para la prueba. Para producción, el almacenamiento
  de idempotencia debería sustituirse por Redis o una base de datos con
  operaciones atómicas, y el procesamiento podría envolverse en una cola
  con workers.
