import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';

typedef OnWidgetSizeChange = void Function(Size size);

class MeasureSize extends SingleChildRenderObjectWidget {
  final OnWidgetSizeChange onChange;

  const MeasureSize({super.key, required this.onChange, required Widget child})
    : super(child: child);

  @override
  RenderObject createRenderObject(BuildContext context) {
    return MeasureSizeRenderObject(onChange);
  }

  @override
  void updateRenderObject(
    BuildContext context,
    covariant MeasureSizeRenderObject renderObject,
  ) {
    renderObject.onChange = onChange;
  }
}

class MeasureSizeRenderObject extends RenderProxyBox {
  MeasureSizeRenderObject(this.onChange);

  OnWidgetSizeChange onChange;
  Size? _oldSize;

  @override
  void performLayout() {
    super.performLayout();
    Size? newSize = child?.size;
    if (_oldSize == newSize || newSize == null) return;
    _oldSize = newSize;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      onChange(newSize);
    });
  }
}
