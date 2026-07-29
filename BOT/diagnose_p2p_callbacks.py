import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))

async def diagnose_callbacks():
    print("🔍 Диагностика P2P callback обработчиков...\n")

    try:
        from app.bot.handlers.p2p import router

        callback_handlers = router.callback_query.handlers

        print(f"📊 Найдено {len(callback_handlers)} callback обработчиков:\n")

        target_callbacks = ["offer_publish", "pt_15", "back_to_pay_time_from_confirm"]
        found_handlers = {}

        for i, handler in enumerate(callback_handlers):
            handler_info = str(handler)
            print(f"Handler {i+1}: {handler_info}")

            if hasattr(handler, 'filters'):
                for filter_obj in handler.filters:
                    filter_str = str(filter_obj)
                    print(f"   Filter: {filter_str}")

                    for target in target_callbacks:
                        if target in filter_str:
                            found_handlers[target] = True
                            print(f"   ✅ Найден обработчик для {target}")
            print()

        print("🎯 Результаты диагностики:")
        for target in target_callbacks:
            if target in found_handlers:
                print(f"✅ {target} - НАЙДЕН")
            else:
                print(f"❌ {target} - НЕ НАЙДЕН")

        print("\n🔄 Проверка состояний FSM:")
        from app.bot.handlers.p2p import CreateOfferStates

        for attr_name in dir(CreateOfferStates):
            if not attr_name.startswith('_'):
                state_obj = getattr(CreateOfferStates, attr_name)
                print(f"   State: {attr_name} = {state_obj}")

        return True

    except Exception as e:
        print(f"❌ Ошибка при диагностике: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(diagnose_callbacks())

    if success:
        print("\n🎉 Диагностика завершена!")
        print("\n💡 Рекомендации:")
        print("1. Убедитесь, что состояния FSM правильные")
        print("2. Проверьте регистрацию роутера в main.py")
        print("3. Перезапустите бота для применения изменений")
    else:
        print("\n⚠️ Обнаружены проблемы при диагностике")
