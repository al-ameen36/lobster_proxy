import litellm


async def generate_response(model, messages):

    response = await litellm.acompletion(model=model, messages=messages)

    return response
