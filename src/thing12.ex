defmodule Fixture12 do
  def compute(value) do
    if value > 0, do: value, else: -value
  end
end
