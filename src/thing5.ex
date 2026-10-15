defmodule Fixture5 do
  def compute(value) do
    if value > 0, do: value, else: -value
  end
end
