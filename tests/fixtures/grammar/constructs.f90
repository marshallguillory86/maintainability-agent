! Every control-flow construct in the Fortran standard that can carry a
! decision. One procedure per construct.

subroutine if_else(v, r)
  integer, intent(in) :: v
  integer, intent(out) :: r
  if (v > 0) then
     r = 1
  else if (v < 0) then
     r = -1
  else
     r = 0
  end if
end subroutine if_else

subroutine do_loop(n, total)
  integer, intent(in) :: n
  integer, intent(out) :: total
  integer :: i
  total = 0
  do i = 1, n
     total = total + i
  end do
end subroutine do_loop

subroutine do_while_loop(n, r)
  integer, intent(in) :: n
  integer, intent(out) :: r
  r = n
  do while (r > 0)
     r = r - 1
  end do
end subroutine do_while_loop

subroutine select_case(v, r)
  integer, intent(in) :: v
  integer, intent(out) :: r
  select case (v)
  case (1)
     r = 1
  case (2)
     r = 2
  case default
     r = 0
  end select
end subroutine select_case

subroutine word_operators(a, b, r)
  logical, intent(in) :: a, b
  logical, intent(out) :: r
  r = a .and. b .or. .not. a
end subroutine word_operators

subroutine where_construct(a)
  real, intent(inout) :: a(:)
  where (a > 0.0)
     a = a * 2.0
  end where
end subroutine where_construct
